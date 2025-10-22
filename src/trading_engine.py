"""
核心交易引擎
负责执行交易策略、风险管理、订单管理等核心功能
"""

import asyncio
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN

from .binance_client import BinanceClient
from .simulated_client import get_client
from .hybrid_client import get_hybrid_client
from .indicators import TechnicalIndicators
from .config_loader import ConfigLoader


class TradingEngine:
    """核心交易引擎类"""
    
    def __init__(self, config_loader: ConfigLoader):
        """
        初始化交易引擎
        
        Args:
            config_loader: 配置加载器实例
        """
        self.config_loader = config_loader
        self.config = config_loader.get_config()
        
        # 根据交易模式选择客户端
        trading_mode = self.config.get('trading_mode', {}).get('mode', 'simulated')
        if trading_mode == 'hybrid':
            self.binance_client = get_hybrid_client(config_loader)
        else:
            self.binance_client = get_client(config_loader)
        
        self.indicators = TechnicalIndicators()
        
        # 交易状态
        self.current_position: Optional[Dict[str, Any]] = None
        self.trade_history: List[Dict[str, Any]] = []
        self.klines_data: Dict[str, List[Dict[str, Any]]] = {}
        self.account_balance: Optional[float] = None
        self.equity_value: Optional[float] = None
        self.max_drawdown: float = 0.0
        self.peak_equity: Optional[float] = None
        
        # 统计信息
        self.total_trades: int = 0
        self.profitable_trades: int = 0
        self.total_profit: float = 0.0
        self.total_fees: float = 0.0
        
        # 时间控制
        self.last_trade_time: Optional[float] = None
        self.last_balance_check: Optional[float] = None
        
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """初始化交易引擎"""
        await self.binance_client.initialize()
        
        # 加载历史K线数据
        await self.load_historical_data()
        
        # 获取账户信息
        await self.update_account_info()
        
        self.logger.info("交易引擎初始化完成")
    
    async def close(self):
        """关闭交易引擎"""
        await self.binance_client.close()
        self.logger.info("交易引擎已关闭")
    
    async def load_historical_data(self):
        """加载历史K线数据"""
        trading_config = self.config['trading']
        kline_config = self.config['kline']
        
        symbol = trading_config['symbol']
        intervals = kline_config['intervals']
        
        for interval in intervals:
            try:
                klines = await self.binance_client.get_klines(
                    symbol=symbol,
                    interval=interval,
                    limit=kline_config['history_limit']
                )
                
                # 转换K线数据格式
                formatted_klines = []
                for kline in klines:
                    formatted_klines.append({
                        'timestamp': kline[0],
                        'open': float(kline[1]),
                        'high': float(kline[2]),
                        'low': float(kline[3]),
                        'close': float(kline[4]),
                        'volume': float(kline[5]),
                        'close_time': kline[6],
                        'quote_volume': float(kline[7]),
                        'trades': kline[8],
                        'taker_buy_volume': float(kline[9]),
                        'taker_buy_quote_volume': float(kline[10])
                    })
                
                self.klines_data[interval] = formatted_klines
                self.logger.info(f"已加载{len(formatted_klines)}条{interval}周期历史K线数据")
                
            except Exception as e:
                self.logger.error(f"加载{interval}历史数据失败: {e}")
    
    async def update_account_info(self):
        """更新账户信息"""
        try:
            # 获取账户余额
            balance_data = await self.binance_client.get_balance()
            usdt_balance = next((item for item in balance_data 
                               if item['asset'] == 'USDT'), None)
            
            if usdt_balance:
                self.account_balance = float(usdt_balance['balance'])
            
            # 获取持仓信息
            trading_config = self.config['trading']
            positions = await self.binance_client.get_position_info(
                trading_config['symbol']
            )
            
            if positions:
                self.current_position = positions[0]
                
                # 计算权益价值
                if self.current_position['positionAmt'] != '0':
                    position_amount = float(self.current_position['positionAmt'])
                    entry_price = float(self.current_position['entryPrice'])
                    current_price = await self.get_current_price()
                    
                    if position_amount > 0:  # 多仓
                        unrealized_pnl = (current_price - entry_price) * position_amount
                    else:  # 空仓
                        unrealized_pnl = (entry_price - current_price) * abs(position_amount)
                    
                    self.equity_value = self.account_balance + unrealized_pnl
                else:
                    self.equity_value = self.account_balance
                    self.current_position = None
            
            # 更新最大回撤
            await self.update_drawdown()
            
            self.last_balance_check = time.time()
            
        except Exception as e:
            self.logger.error(f"更新账户信息失败: {e}")
    
    async def update_drawdown(self):
        """更新最大回撤"""
        if self.equity_value is not None:
            if self.peak_equity is None or self.equity_value > self.peak_equity:
                self.peak_equity = self.equity_value
            
            if self.peak_equity > 0:
                drawdown = (self.peak_equity - self.equity_value) / self.peak_equity
                self.max_drawdown = max(self.max_drawdown, drawdown)
    
    async def get_current_price(self) -> float:
        """获取当前价格"""
        trading_config = self.config['trading']
        try:
            ticker = await self.binance_client.get_ticker_price(
                trading_config['symbol']
            )
            return float(ticker['price'])
        except Exception as e:
            self.logger.error(f"获取当前价格失败: {e}")
            return 0.0
    
    def is_drawdown_limit_reached(self) -> bool:
        """检查是否达到最大回撤限制"""
        risk_config = self.config['risk_management']
        return self.max_drawdown >= risk_config['max_drawdown']
    
    def can_trade(self) -> bool:
        """检查是否可以交易"""
        # 检查最大回撤限制
        if self.is_drawdown_limit_reached():
            self.logger.warning("已达到最大回撤限制，暂停交易")
            return False
        
        # 检查交易时间间隔
        trading_config = self.config['trading']
        if self.last_trade_time and \
           time.time() - self.last_trade_time < trading_config['min_trade_interval']:
            return False
        
        return True
    
    async def analyze_market(self) -> Dict[str, Any]:
        """分析市场并生成交易信号"""
        trading_config = self.config['trading']
        indicators_config = self.config['indicators']
        
        # 获取主要周期的收盘价数据
        main_interval = trading_config['main_interval']
        if main_interval not in self.klines_data:
            return {'overall_signal': 'hold'}
        
        close_prices = [kline['close'] for kline in self.klines_data[main_interval]]
        
        if len(close_prices) < 50:  # 需要足够的数据
            return {'overall_signal': 'hold'}
        
        # 生成交易信号
        signals = self.indicators.generate_signals(close_prices, indicators_config)
        
        # 检查震荡条件
        oscillation_config = self.config['oscillation_filter']
        if signals['is_oscillating'] and not oscillation_config['trade_during_oscillation']:
            self.logger.info("市场处于震荡状态，避免交易")
            signals['overall_signal'] = 'hold'
        
        return signals
    
    async def execute_trade(self, signal: str, current_price: float):
        """执行交易"""
        if not self.can_trade():
            return
        
        trading_config = self.config['trading']
        risk_config = self.config['risk_management']
        fee_config = self.config['fees']
        
        symbol = trading_config['symbol']
        leverage = trading_config['leverage']
        
        try:
            # 计算交易数量
            position_size = self.calculate_position_size(current_price)
            
            if position_size <= 0:
                self.logger.warning("交易数量计算为0，跳过交易")
                return
            
            order_side = 'BUY' if signal == 'buy' else 'SELL'
            order_type = 'MARKET'  # 使用市价单
            
            # 创建订单
            order = await self.binance_client.create_order(
                symbol=symbol,
                side=order_side,
                order_type=order_type,
                quantity=position_size
            )
            
            # 记录交易
            trade_record = {
                'timestamp': time.time(),
                'datetime': datetime.now().isoformat(),
                'symbol': symbol,
                'side': order_side,
                'type': order_type,
                'quantity': position_size,
                'price': current_price,
                'order_id': order['orderId'],
                'client_order_id': order['clientOrderId'],
                'status': order['status'],
                'fee': self.calculate_fee(position_size, current_price, order_side)
            }
            
            self.trade_history.append(trade_record)
            self.total_trades += 1
            self.last_trade_time = time.time()
            
            self.logger.info(f"已执行{order_side}交易: {position_size} {symbol} @ {current_price}")
            
            # 更新账户信息
            await self.update_account_info()
            
        except Exception as e:
            self.logger.error(f"执行交易失败: {e}")
    
    def calculate_position_size(self, current_price: float) -> float:
        """计算交易头寸大小"""
        risk_config = self.config['risk_management']
        
        if self.account_balance is None:
            return 0.0
        
        # 计算风险资金
        risk_capital = self.account_balance * risk_config['risk_per_trade']
        
        # 根据ATR计算止损距离（这里简化处理）
        stop_loss_pct = risk_config['stop_loss_pct']
        
        # 计算头寸大小
        position_size = (risk_capital / current_price) / stop_loss_pct
        
        # 应用精度
        precision = self.config['execution']['quantity_precision']
        position_size = round(position_size, precision)
        
        # 确保最小交易量
        min_quantity = self.config['execution']['min_quantity']
        if position_size < min_quantity:
            return 0.0
        
        return position_size
    
    def calculate_fee(self, quantity: float, price: float, side: str) -> float:
        """计算交易手续费"""
        fee_config = self.config['fees']
        trading_config = self.config['trading']
        
        # 计算交易总价值（考虑杠杆）
        leverage = trading_config['leverage']
        trade_value = quantity * price * leverage
        
        # 假设市价单使用taker费率
        fee_rate = fee_config['taker']
        fee = trade_value * fee_rate
        
        self.total_fees += fee
        return fee
    
    async def close_all_positions(self):
        """平掉所有仓位"""
        if not self.current_position:
            return
        
        trading_config = self.config['trading']
        symbol = trading_config['symbol']
        
        try:
            position_amount = float(self.current_position['positionAmt'])
            
            if position_amount != 0:
                # 获取当前价格
                current_price = await self.get_current_price()
                
                # 平仓方向与持仓相反
                close_side = 'SELL' if position_amount > 0 else 'BUY'
                close_quantity = abs(position_amount)
                
                # 创建平仓订单
                order = await self.binance_client.create_order(
                    symbol=symbol,
                    side=close_side,
                    order_type='MARKET',
                    quantity=close_quantity,
                    reduce_only=True
                )
                
                # 记录平仓交易
                trade_record = {
                    'timestamp': time.time(),
                    'datetime': datetime.now().isoformat(),
                    'symbol': symbol,
                    'side': close_side,
                    'type': 'MARKET',
                    'quantity': close_quantity,
                    'price': current_price,
                    'order_id': order['orderId'],
                    'client_order_id': order['clientOrderId'],
                    'status': order['status'],
                    'fee': self.calculate_fee(close_quantity, current_price, close_side)
                }
                
                self.trade_history.append(trade_record)
                self.total_trades += 1
                self.last_trade_time = time.time()
                
                self.logger.info(f"已平仓: {close_quantity} {symbol} @ {current_price}")
                
                # 更新账户信息
                await self.update_account_info()
                
        except Exception as e:
            self.logger.error(f"平仓失败: {e}")
    
    async def run_trading_cycle(self):
        """运行一个完整的交易周期"""
        try:
            # 更新市场数据
            await self.update_market_data()
            
            # 更新账户信息（定期更新）
            if not self.last_balance_check or \
               time.time() - self.last_balance_check > 300:  # 5分钟更新一次
                await self.update_account_info()
            
            # 分析市场
            signals = await self.analyze_market()
            
            # 获取当前价格
            current_price = await self.get_current_price()
            
            # 执行交易决策
            if signals['overall_signal'] != 'hold':
                await self.execute_trade(signals['overall_signal'], current_price)
            
            # 记录交易日志
            self.log_trading_status(signals, current_price)
            
        except Exception as e:
            self.logger.error(f"交易周期执行失败: {e}")
    
    async def update_market_data(self):
        """更新市场数据"""
        # 这里可以添加实时数据更新逻辑
        # 目前使用历史数据，实际交易中需要通过WebSocket获取实时数据
        pass
    
    def log_trading_status(self, signals: Dict[str, Any], current_price: float):
        """记录交易状态日志"""
        status = {
            'timestamp': time.time(),
            'datetime': datetime.now().isoformat(),
            'current_price': current_price,
            'account_balance': self.account_balance,
            'equity_value': self.equity_value,
            'max_drawdown': self.max_drawdown,
            'current_position': self.current_position,
            'signal': signals['overall_signal'],
            'total_trades': self.total_trades,
            'profitable_trades': self.profitable_trades,
            'total_profit': self.total_profit,
            'total_fees': self.total_fees
        }
        
        self.logger.info(f"交易状态: {status}")
    
    def get_trading_stats(self) -> Dict[str, Any]:
        """获取交易统计信息"""
        win_rate = (self.profitable_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        avg_profit = (self.total_profit / self.total_trades) if self.total_trades > 0 else 0
        
        return {
            'total_trades': self.total_trades,
            'profitable_trades': self.profitable_trades,
            'win_rate': win_rate,
            'total_profit': self.total_profit,
            'total_fees': self.total_fees,
            'net_profit': self.total_profit - self.total_fees,
            'max_drawdown': self.max_drawdown,
            'current_balance': self.account_balance,
            'equity_value': self.equity_value,
            'peak_equity': self.peak_equity
        }
    
    async def monitor_risk(self):
        """监控风险"""
        if self.is_drawdown_limit_reached():
            self.logger.critical("达到最大回撤限制，停止交易并平仓")
            await self.close_all_positions()
            return False
        
        return True