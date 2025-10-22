"""
模拟交易客户端 - 不使用真实API，完全模拟交易环境
"""

import asyncio
import time
import logging
import random
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from .config_loader import ConfigLoader


class SimulatedBinanceClient:
    """模拟币安API客户端"""
    
    def __init__(self, config_loader: ConfigLoader):
        """
        初始化模拟客户端
        
        Args:
            config_loader: 配置加载器实例
        """
        self.config_loader = config_loader
        self.config = config_loader.get_config()
        self.trading_mode_config = self.config.get('trading_mode', {})
        
        # 模拟账户数据
        self.initial_balance = self.trading_mode_config.get('initial_balance', 1000.0)
        self.account_balance = self.initial_balance
        self.available_balance = self.initial_balance
        self.positions = {}
        self.trade_history = []
        self.order_history = []
        
        # 模拟市场数据
        trading_config = self.config['trading']
        self.symbol = trading_config['symbol']
        self.initial_price = self.trading_mode_config.get('simulated_price', 50000.0)
        self.current_price = self.initial_price
        self.price_volatility = self.trading_mode_config.get('price_volatility', 0.005)
        self.price_history = []
        
        self.logger = logging.getLogger(__name__)
        self.initialized = False
    
    async def initialize(self):
        """初始化模拟客户端"""
        self.logger.info("初始化模拟交易客户端...")
        
        # 生成初始价格历史
        self._generate_price_history()
        
        self.initialized = True
        self.logger.info(f"模拟交易客户端初始化完成，初始资金: {self.account_balance} USDT")
        self.logger.info(f"初始价格: {self.current_price} USDT")
        
        return True
    
    async def close(self):
        """关闭客户端"""
        self.logger.info("模拟交易客户端已关闭")
    
    def _generate_price_history(self):
        """生成模拟价格历史"""
        current_time = datetime.now()
        price = self.initial_price
        
        for i in range(1000):
            timestamp = current_time - timedelta(minutes=5 * (1000 - i))
            
            # 模拟价格波动
            change_percent = random.uniform(-self.price_volatility, self.price_volatility)
            price = price * (1 + change_percent)
            
            self.price_history.append({
                'timestamp': timestamp.timestamp(),
                'open': price,
                'high': price * (1 + abs(change_percent)),
                'low': price * (1 - abs(change_percent)),
                'close': price,
                'volume': random.uniform(100, 1000)
            })
    
    def _update_price(self):
        """更新当前价格"""
        if not self.price_history:
            return
        
        last_price = self.price_history[-1]['close']
        change_percent = random.uniform(-self.price_volatility, self.price_volatility)
        self.current_price = last_price * (1 + change_percent)
        
        # 添加新的价格记录
        self.price_history.append({
            'timestamp': time.time(),
            'open': last_price,
            'high': max(last_price, self.current_price),
            'low': min(last_price, self.current_price),
            'close': self.current_price,
            'volume': random.uniform(50, 500)
        })
    
    async def get_balance(self) -> List[Dict[str, Any]]:
        """获取模拟账户余额"""
        if not self.initialized:
            await self.initialize()
        
        return [{
            'asset': 'USDT',
            'walletBalance': str(self.account_balance),
            'availableBalance': str(self.available_balance),
            'balance': str(self.account_balance)
        }]
    
    async def get_account_info(self) -> Dict[str, Any]:
        """获取模拟账户信息"""
        if not self.initialized:
            await self.initialize()
        
        # 计算持仓盈亏
        total_unrealized_profit = 0.0
        positions = []
        
        for symbol, position in self.positions.items():
            entry_price = position['entry_price']
            quantity = position['quantity']
            side = position['side']
            leverage = position['leverage']
            
            if side == 'LONG':
                unrealized_profit = (self.current_price - entry_price) * quantity * leverage
            else:  # SHORT
                unrealized_profit = (entry_price - self.current_price) * quantity * leverage
            
            total_unrealized_profit += unrealized_profit
            
            positions.append({
                'symbol': symbol,
                'positionAmt': str(quantity),
                'entryPrice': str(entry_price),
                'unRealizedProfit': str(unrealized_profit),
                'leverage': str(leverage),
                'positionSide': side
            })
        
        return {
            'totalWalletBalance': str(self.account_balance),
            'totalUnrealizedProfit': str(total_unrealized_profit),
            'availableBalance': str(self.available_balance),
            'assets': [{
                'asset': 'USDT',
                'walletBalance': str(self.account_balance),
                'availableBalance': str(self.available_balance)
            }],
            'positions': positions
        }
    
    async def get_position_info(self, symbol: str) -> List[Dict[str, Any]]:
        """获取模拟持仓信息"""
        if not self.initialized:
            await self.initialize()
        
        positions = []
        if symbol in self.positions:
            position = self.positions[symbol]
            if position['quantity'] != 0:
                positions.append({
                    'symbol': symbol,
                    'positionAmt': str(position['quantity']),
                    'entryPrice': str(position['entry_price']),
                    'unRealizedProfit': '0',  # 简化处理
                    'leverage': str(position['leverage']),
                    'positionSide': position['side']
                })
        
        return positions
    
    async def get_ticker_price(self, symbol: str) -> Dict[str, Any]:
        """获取模拟价格"""
        if not self.initialized:
            await self.initialize()
        
        self._update_price()
        
        return {
            'symbol': symbol,
            'price': str(self.current_price),
            'time': int(time.time() * 1000)
        }
    
    async def get_klines(self, symbol: str, interval: str, 
                       limit: int = 1000, **kwargs) -> List[List[Any]]:
        """获取模拟K线数据"""
        if not self.initialized:
            await self.initialize()
        
        if not self.price_history:
            self._generate_price_history()
        
        # 返回指定数量的K线数据
        recent_data = self.price_history[-limit:] if limit < len(self.price_history) else self.price_history
        
        klines = []
        for data in recent_data:
            klines.append([
                int(data['timestamp'] * 1000),  # open time
                str(data['open']),              # open
                str(data['high']),              # high
                str(data['low']),               # low
                str(data['close']),             # close
                str(data['volume']),            # volume
                int(data['timestamp'] * 1000) + 300000,  # close time
                '0',                           # quote asset volume
                0,                             # number of trades
                '0',                           # taker buy base asset volume
                '0',                           # taker buy quote asset volume
                '0'                            # ignore
            ])
        
        return klines
    
    async def create_order(self, symbol: str, side: str, order_type: str,
                         quantity: float, **kwargs) -> Dict[str, Any]:
        """创建模拟订单"""
        if not self.initialized:
            await self.initialize()
        
        self._update_price()
        
        # 获取交易配置
        trading_config = self.config['trading']
        leverage = trading_config['leverage']
        
        # 计算订单价值
        order_value = quantity * self.current_price * leverage
        
        # 检查资金是否足够
        if order_value > self.available_balance:
            raise Exception(f"资金不足，需要 {order_value:.2f} USDT，可用 {self.available_balance:.2f} USDT")
        
        # 生成订单ID
        order_id = int(time.time() * 1000)
        
        # 记录订单
        order = {
            'orderId': order_id,
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'origQty': str(quantity),
            'executedQty': str(quantity),
            'price': str(self.current_price),
            'status': 'FILLED',
            'timeInForce': 'GTC',
            'cummulativeQuoteQty': str(order_value),
            'updateTime': int(time.time() * 1000)
        }
        
        self.order_history.append(order)
        
        # 更新持仓
        if symbol not in self.positions:
            self.positions[symbol] = {
                'quantity': 0.0,
                'entry_price': 0.0,
                'side': None,
                'leverage': leverage
            }
        
        position = self.positions[symbol]
        
        if side == 'BUY':
            if position['side'] == 'SHORT':
                # 平空仓
                self.available_balance += position['quantity'] * self.current_price * leverage
                position['quantity'] = 0.0
                position['side'] = None
            
            # 开多仓
            position['quantity'] += quantity
            position['entry_price'] = self.current_price
            position['side'] = 'LONG'
            
        else:  # SELL
            if position['side'] == 'LONG':
                # 平多仓
                self.available_balance += position['quantity'] * self.current_price * leverage
                position['quantity'] = 0.0
                position['side'] = None
            
            # 开空仓
            position['quantity'] += quantity
            position['entry_price'] = self.current_price
            position['side'] = 'SHORT'
        
        # 扣除保证金
        self.available_balance -= order_value
        
        # 计算手续费
        fees_config = self.config['fees']
        fee_rate = fees_config['taker'] if order_type == 'MARKET' else fees_config['maker']
        fee = order_value * fee_rate
        
        # 记录交易
        trade = {
            'timestamp': time.time(),
            'symbol': symbol,
            'side': side.lower(),
            'quantity': quantity,
            'price': self.current_price,
            'order_id': order_id,
            'fee': fee,
            'realized_pnl': 0.0  # 平仓时计算
        }
        self.trade_history.append(trade)
        
        self.logger.info(f"模拟订单执行: {side} {quantity} {symbol} @ {self.current_price:.2f}")
        self.logger.info(f"手续费: {fee:.4f} USDT, 剩余可用资金: {self.available_balance:.2f} USDT")
        
        return order
    
    async def cancel_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """取消模拟订单"""
        # 在模拟环境中，订单立即执行，所以取消操作通常无效
        return {'status': 'CANCELED', 'orderId': order_id}
    
    async def get_order(self, symbol: str, order_id: int) -> Dict[str, Any]:
        """获取模拟订单信息"""
        for order in self.order_history:
            if order['orderId'] == order_id:
                return order
        raise Exception("订单不存在")
    
    async def get_all_orders(self, symbol: str, **kwargs) -> List[Dict[str, Any]]:
        """获取所有模拟订单"""
        return self.order_history
    
    async def get_trade_history(self, symbol: str, **kwargs) -> List[Dict[str, Any]]:
        """获取模拟交易历史"""
        return self.trade_history


def get_client(config_loader: ConfigLoader):
    """获取交易客户端实例（模拟或真实）"""
    config = config_loader.get_config()
    trading_mode = config.get('trading_mode', {}).get('mode', 'simulated')
    
    if trading_mode == 'simulated':
        return SimulatedBinanceClient(config_loader)
    else:
        from .binance_client import BinanceClient
        return BinanceClient(config_loader)