"""
币安API客户端
提供REST API和WebSocket接口的封装
"""

import hmac
import hashlib
import time
import logging
from typing import Dict, List, Any, Optional, Callable
from urllib.parse import urlencode

import aiohttp
import websockets
import json
from datetime import datetime

from .config_loader import ConfigLoader


class BinanceClient:
    """币安API客户端类"""
    
    def __init__(self, config_loader: ConfigLoader):
        """
        初始化币安客户端
        
        Args:
            config_loader: 配置加载器实例
        """
        self.config_loader = config_loader
        self.config = config_loader.get_config()
        self.binance_config = self.config['binance']
        
        self.api_key = self.binance_config['api_key']
        self.api_secret = self.binance_config['api_secret']
        self.testnet = self.binance_config['testnet']
        
        # 选择API端点
        if self.testnet:
            self.base_url = self.binance_config['testnet_url']
            self.websocket_url = self.binance_config['testnet_websocket_url']
        else:
            self.base_url = self.binance_config['base_url']
            self.websocket_url = self.binance_config['websocket_url']
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.logger = logging.getLogger(__name__)
        
        # 请求计数器（用于限流控制）
        self.request_count = 0
        self.last_request_time = time.time()
    
    async def initialize(self):
        """初始化客户端会话"""
        if self.session is None:
            self.session = aiohttp.ClientSession(
                headers={
                    'X-MBX-APIKEY': self.api_key,
                    'Content-Type': 'application/json'
                }
            )
        self.logger.info("币安客户端初始化完成")
    
    async def close(self):
        """关闭客户端会话"""
        if self.session:
            await self.session.close()
            self.session = None
        
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        self.logger.info("币安客户端已关闭")
    
    def _generate_signature(self, params: Dict[str, Any]) -> str:
        """
        生成HMAC SHA256签名
        
        Args:
            params: 请求参数
            
        Returns:
            str: 签名字符串
        """
        query_string = urlencode(params)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _add_required_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        添加必需的请求参数
        
        Args:
            params: 原始参数
            
        Returns:
            Dict[str, Any]: 包含必需参数的参数字典
        """
        params = params.copy()
        params['timestamp'] = int(time.time() * 1000)
        
        # 添加签名
        if self.api_secret:
            params['signature'] = self._generate_signature(params)
        
        return params
    
    async def _make_request(self, method: str, endpoint: str, 
                          params: Optional[Dict[str, Any]] = None,
                          signed: bool = False) -> Dict[str, Any]:
        """
        发送HTTP请求
        
        Args:
            method: HTTP方法 (GET, POST, DELETE, PUT)
            endpoint: API端点路径
            params: 请求参数
            signed: 是否需要签名
            
        Returns:
            Dict[str, Any]: 响应数据
            
        Raises:
            Exception: 请求失败时抛出异常
        """
        if params is None:
            params = {}
        
        # 添加签名参数
        if signed:
            params = self._add_required_params(params)
        
        url = f"{self.base_url}{endpoint}"
        
        # 控制请求频率（避免触发限流）
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        if elapsed < 0.1:  # 最小请求间隔100ms
            await asyncio.sleep(0.1 - elapsed)
        
        try:
            async with self.session.request(method, url, params=params) as response:
                self.request_count += 1
                self.last_request_time = time.time()
                
                # 检查响应状态
                if response.status != 200:
                    error_text = await response.text()
                    self.logger.error(f"API请求失败: {response.status} - {error_text}")
                    raise Exception(f"API请求失败: {response.status}")
                
                data = await response.json()
                
                # 检查币安API错误码
                if isinstance(data, dict) and 'code' in data and data['code'] != 200:
                    self.logger.error(f"币安API错误: {data['code']} - {data.get('msg', 'Unknown error')}")
                    raise Exception(f"币安API错误: {data['code']}")
                
                return data
                
        except aiohttp.ClientError as e:
            self.logger.error(f"网络请求错误: {e}")
            raise
        except Exception as e:
            self.logger.error(f"请求处理错误: {e}")
            raise
    
    # ==================== 市场数据API ====================
    
    async def get_exchange_info(self) -> Dict[str, Any]:
        """获取交易对信息"""
        endpoint = "/fapi/v1/exchangeInfo"
        return await self._make_request('GET', endpoint)
    
    async def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """获取指定交易对信息"""
        exchange_info = await self.get_exchange_info()
        for symbol_info in exchange_info['symbols']:
            if symbol_info['symbol'] == symbol:
                return symbol_info
        return None
    
    async def get_klines(self, symbol: str, interval: str, 
                       limit: int = 1000, start_time: Optional[int] = None,
                       end_time: Optional[int] = None) -> List[List[Any]]:
        """
        获取K线数据
        
        Args:
            symbol: 交易对
            interval: K线周期
            limit: 数据条数
            start_time: 开始时间戳
            end_time: 结束时间戳
            
        Returns:
            List[List[Any]]: K线数据列表
        """
        endpoint = "/fapi/v1/klines"
        params = {
            'symbol': symbol,
            'interval': interval,
            'limit': limit
        }
        
        if start_time:
            params['startTime'] = start_time
        if end_time:
            params['endTime'] = end_time
        
        return await self._make_request('GET', endpoint, params)
    
    async def get_ticker_price(self, symbol: str) -> Dict[str, Any]:
        """获取最新价格"""
        endpoint = "/fapi/v1/ticker/price"
        params = {'symbol': symbol}
        return await self._make_request('GET', endpoint, params)
    
    async def get_orderbook(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """获取深度数据"""
        endpoint = "/fapi/v1/depth"
        params = {
            'symbol': symbol,
            'limit': limit
        }
        return await self._make_request('GET', endpoint, params)
    
    # ==================== 账户信息API ====================
    
    async def get_account_info(self) -> Dict[str, Any]:
        """获取账户信息"""
        endpoint = "/fapi/v2/account"
        return await self._make_request('GET', endpoint, signed=True)
    
    async def get_balance(self) -> List[Dict[str, Any]]:
        """获取账户余额"""
        endpoint = "/fapi/v2/balance"
        return await self._make_request('GET', endpoint, signed=True)
    
    async def get_position_info(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取持仓信息"""
        endpoint = "/fapi/v2/positionRisk"
        params = {}
        if symbol:
            params['symbol'] = symbol
        return await self._make_request('GET', endpoint, params, signed=True)
    
    # ==================== 交易API ====================
    
    async def create_order(self, symbol: str, side: str, order_type: str,
                         quantity: float, price: Optional[float] = None,
                         time_in_force: str = "GTC", 
                         reduce_only: bool = False,
                         close_position: bool = False,
                         stop_price: Optional[float] = None,
                         activation_price: Optional[float] = None,
                         callback_rate: Optional[float] = None) -> Dict[str, Any]:
        """
        创建订单
        
        Args:
            symbol: 交易对
            side: 方向 (BUY/SELL)
            order_type: 订单类型 (LIMIT/MARKET/STOP_MARKET/STOP/TAKE_PROFIT/etc.)
            quantity: 数量
            price: 价格（限价单需要）
            time_in_force: 订单有效期
            reduce_only: 是否只减仓
            close_position: 是否平仓
            stop_price: 止损价格
            activation_price: 激活价格
            callback_rate: 回调比例
            
        Returns:
            Dict[str, Any]: 订单信息
        """
        endpoint = "/fapi/v1/order"
        params = {
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': quantity,
            'timeInForce': time_in_force,
            'reduceOnly': reduce_only,
            'closePosition': close_position
        }
        
        if price:
            params['price'] = price
        if stop_price:
            params['stopPrice'] = stop_price
        if activation_price:
            params['activationPrice'] = activation_price
        if callback_rate:
            params['callbackRate'] = callback_rate
        
        return await self._make_request('POST', endpoint, params, signed=True)
    
    async def cancel_order(self, symbol: str, order_id: Optional[int] = None,
                         orig_client_order_id: Optional[str] = None) -> Dict[str, Any]:
        """取消订单"""
        endpoint = "/fapi/v1/order"
        params = {'symbol': symbol}
        
        if order_id:
            params['orderId'] = order_id
        if orig_client_order_id:
            params['origClientOrderId'] = orig_client_order_id
        
        return await self._make_request('DELETE', endpoint, params, signed=True)
    
    async def get_order(self, symbol: str, order_id: Optional[int] = None,
                      orig_client_order_id: Optional[str] = None) -> Dict[str, Any]:
        """查询订单"""
        endpoint = "/fapi/v1/order"
        params = {'symbol': symbol}
        
        if order_id:
            params['orderId'] = order_id
        if orig_client_order_id:
            params['origClientOrderId'] = orig_client_order_id
        
        return await self._make_request('GET', endpoint, params, signed=True)
    
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """查询当前挂单"""
        endpoint = "/fapi/v1/openOrders"
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        return await self._make_request('GET', endpoint, params, signed=True)
    
    async def cancel_all_orders(self, symbol: str) -> List[Dict[str, Any]]:
        """取消所有订单"""
        endpoint = "/fapi/v1/allOpenOrders"
        params = {'symbol': symbol}
        return await self._make_request('DELETE', endpoint, params, signed=True)
    
    # ==================== WebSocket连接 ====================
    
    async def connect_websocket(self):
        """连接WebSocket"""
        try:
            self.websocket = await websockets.connect(self.websocket_url)
            self.logger.info("WebSocket连接已建立")
        except Exception as e:
            self.logger.error(f"WebSocket连接失败: {e}")
            raise
    
    async def subscribe_klines(self, symbol: str, interval: str):
        """订阅K线数据"""
        if not self.websocket:
            await self.connect_websocket()
        
        stream_name = f"{symbol.lower()}@kline_{interval}"
        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": [stream_name],
            "id": 1
        }
        
        await self.websocket.send(json.dumps(subscribe_message))
        self.logger.info(f"已订阅K线数据: {stream_name}")
    
    async def subscribe_user_data(self):
        """订阅用户数据流"""
        if not self.websocket:
            await self.connect_websocket()
        
        # 首先获取listenKey
        listen_key = await self._get_listen_key()
        
        stream_name = f"{listen_key}"
        subscribe_message = {
            "method": "SUBSCRIBE",
            "params": [stream_name],
            "id": 2
        }
        
        await self.websocket.send(json.dumps(subscribe_message))
        self.logger.info("已订阅用户数据流")
    
    async def _get_listen_key(self) -> str:
        """获取listenKey"""
        endpoint = "/fapi/v1/listenKey"
        response = await self._make_request('POST', endpoint, signed=True)
        return response['listenKey']
    
    async def keep_alive_listen_key(self):
        """保持listenKey有效"""
        endpoint = "/fapi/v1/listenKey"
        await self._make_request('PUT', endpoint, signed=True)
        self.logger.info("listenKey已续期")
    
    async def receive_websocket_messages(self, callback: Callable[[Dict[str, Any]], None]):
        """
        接收WebSocket消息
        
        Args:
            callback: 消息处理回调函数
        """
        if not self.websocket:
            raise Exception("WebSocket未连接")
        
        try:
            async for message in self.websocket:
                data = json.loads(message)
                callback(data)
        except websockets.exceptions.ConnectionClosed:
            self.logger.error("WebSocket连接已关闭")
            raise
        except Exception as e:
            self.logger.error(f"接收WebSocket消息错误: {e}")
            raise
    
    # ==================== 工具方法 ====================
    
    def calculate_quantity(self, symbol: str, usdt_amount: float, 
                         current_price: float) -> float:
        """
        计算交易数量
        
        Args:
            symbol: 交易对
            usdt_amount: USDT金额
            current_price: 当前价格
            
        Returns:
            float: 交易数量
        """
        # 这里需要根据交易对的精度要求进行计算
        # 实际实现中需要查询交易对的精度信息
        quantity = usdt_amount / current_price
        
        # 根据数量精度进行舍入
        quantity_precision = self.config['execution']['quantity_precision']
        quantity = round(quantity, quantity_precision)
        
        return quantity
    
    def format_price(self, price: float) -> float:
        """格式化价格"""
        price_precision = self.config['execution']['price_precision']
        return round(price, price_precision)


# 异步导入
import asyncio