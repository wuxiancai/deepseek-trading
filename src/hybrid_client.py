"""
混合模式交易客户端 - 使用真实的市场数据，但虚拟的资金管理
"""

import asyncio
import time
import logging
import json
from typing import Dict, List, Any, Optional, Callable

import websockets
from .config_loader import ConfigLoader


class HybridBinanceClient:
    """混合模式币安客户端 - 真实市场数据 + 虚拟资金管理"""
    
    def __init__(self, config_loader: ConfigLoader):
        """
        初始化混合客户端
        
        Args:
            config_loader: 配置加载器实例
        """
        self.config_loader = config_loader
        self.config = config_loader.get_config()
        self.binance_config = self.config['binance']
        self.trading_mode_config = self.config.get('trading_mode', {})
        
        # WebSocket配置
        self.testnet = self.binance_config['testnet']
        if self.testnet:
            self.websocket_url = self.binance_config['testnet_websocket_url']
        else:
            self.websocket_url = self.binance_config['websocket_url']
        
        # 模拟账户数据
        self.initial_balance = self.trading_mode_config.get('initial_balance', 1000.0)
        self.account_balance = self.initial_balance
        self.available_balance = self.initial_balance
        self.positions = {}
        self.trade_history = []
        self.order_history = []
        
        # 真实市场数据
        trading_config = self.config['trading']
        self.symbol = trading_config['symbol']
        self.current_price = 0.0
        self.websocket = None
        self.websocket_connected = False
        
        # WebSocket回调
        self.price_callbacks = []
        self.klines_callbacks = []
        
        self.logger = logging.getLogger(__name__)
        self.initialized = False
    
    async def initialize(self):
        """初始化混合客户端"""
        self.logger.info("初始化混合交易客户端...")
        
        try:
            # 连接WebSocket获取实时价格
            await self.connect_websocket()
            await self.subscribe_ticker()
            
            # 等待获取初始价格
            await asyncio.sleep(2)
            
            if self.current_price == 0:
                self.logger.warning("未能获取到实时价格，使用默认价格50000")
                self.current_price = 50000.0
            
            self.initialized = True
            self.logger.info(f"混合交易客户端初始化完成")
            self.logger.info(f"初始资金: {self.account_balance} USDT")
            self.logger.info(f"当前价格: {self.current_price} USDT")
            
            return True
            
        except Exception as e:
            self.logger.error(f"混合客户端初始化失败: {e}")
            # 如果WebSocket连接失败，仍然允许继续运行
            self.current_price = 50000.0
            self.initialized = True
            return True
    
    async def close(self):
        """关闭客户端"""
        if self.websocket:
            await self.websocket.close()
        self.logger.info("混合交易客户端已关闭")
    
    # ==================== WebSocket连接 ====================
    
    async def connect_websocket(self):
        """连接WebSocket"""
        try:
            self.websocket = await websockets.connect(self.websocket_url)
            self.websocket_connected = True
            self.logger.info("WebSocket连接已建立")
            
            # 启动消息接收任务
            asyncio.create_task(self._receive_websocket_messages())
            
        except Exception as e:
            self.logger.error(f"WebSocket连接失败: {e}")
            self.websocket_connected = False
    
    async def subscribe_ticker(self):
        """订阅实时价格"""
        if not self.websocket_connected:
            return
        
        stream_name = f"{self.symbol.lower()}@bookTicker"
        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": [stream_name],
            "id": 1
        }
        
        try:
            await self.websocket.send(json.dumps(subscribe_message))
            self.logger.info(f"已订阅实时价格: {stream_name}")
        except Exception as e:
            self.logger.error(f"订阅实时价格失败: {e}")
    
    async def subscribe_klines(self, interval: str):
        """订阅K线数据"""
        if not self.websocket_connected:
            return
        
        stream_name = f"{self.symbol.lower()}@kline_{interval}"
        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": [stream_name],
            "id": 2
        }
        
        try:
            await self.websocket.send(json.dumps(subscribe_message))
            self.logger.info(f"已订阅K线数据: {stream_name}")
        except Exception as e:
            self.logger.error(f"订阅K线数据失败: {e}")
    
    async def _receive_websocket_messages(self):
        """接收WebSocket消息"""
        while self.websocket_connected:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                # 处理实时价格消息
                if 'b' in data and 'a' in data:  # bookTicker格式
                    best_bid = float(data['b'])
                    best_ask = float(data['a'])
                    self.current_price = (best_bid + best_ask) / 2
                    
                    # 触发价格回调
                    for callback in self.price_callbacks:
                        callback(self.current_price)
                
                # 处理K线消息
                elif 'k' in data:  # kline格式
                    kline_data = data['k']
                    if kline_data['x']:  # 如果是收盘的K线
                        # 触发K线回调
                        for callback in self.klines_callbacks:
                            callback(kline_data)
                            
            except websockets.exceptions.ConnectionClosed:
                self.logger.error("WebSocket连接已关闭")
                self.websocket_connected = False
                break
            except Exception as e:
                self.logger.error(f"处理WebSocket消息错误: {e}")
                await asyncio.sleep(1)
    
    def register_price_callback(self, callback: Callable[[float], None]):
        """注册价格变化回调"""
        self.price_callbacks.append(callback)
    
    def register_klines_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """注册K线数据回调"""
        self.klines_callbacks.append(callback)
    
    # ==================== 账户和交易接口 ====================
    
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
        """获取实时价格"""
        if not self.initialized:
            await self.initialize()
        
        return {
            'symbol': symbol,
            'price': str(self.current_price),
            'time': int(time.time() * 1000)
        }
    
    async def get_klines(self, symbol: str, interval: str, 
                       limit: int = 1000, **kwargs) -> List[List[Any]]:
        """获取K线数据（需要真实API，这里返回空列表）"""
        # 在混合模式下，K线数据需要通过其他方式获取
        # 这里返回空列表，实际使用时需要结合其他数据源
        return []
    
    async def create_order(self, symbol: str, side: str, order_type: str,
                         quantity: float, **kwargs) -> Dict[str, Any]:
        """创建模拟订单"""
        if not self.initialized:
            await self.initialize()
        
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


def get_hybrid_client(config_loader: ConfigLoader):
    """获取混合模式客户端实例"""
    return HybridBinanceClient(config_loader)