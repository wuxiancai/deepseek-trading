#!/usr/bin/env python3
"""
模拟交易系统 - 不使用真实API，使用虚拟1000USDT资金进行模拟交易
"""

import asyncio
import logging
import sys
import os
import time
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config_loader import ConfigLoader

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


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
        self.binance_config = self.config['binance']
        
        # 模拟账户数据
        self.account_balance = 1000.0  # 初始1000USDT
        self.available_balance = 1000.0
        self.positions = {}
        self.trade_history = []
        self.order_history = []
        
        # 模拟市场数据
        self.symbol = self.config['trading']['symbol']
        self.current_price = 50000.0  # 初始BTC价格
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
    
    async def close(self):
        """关闭客户端"""
        self.logger.info("模拟交易客户端已关闭")
    
    def _generate_price_history(self):
        """生成模拟价格历史"""
        current_time = datetime.now()
        price = self.current_price
        
        for i in range(1000):
            timestamp = current_time - timedelta(minutes=5 * (1000 - i))
            
            # 模拟价格波动（±0.5%）
            change_percent = random.uniform(-0.005, 0.005)
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
        change_percent = random.uniform(-0.002, 0.002)  # 小幅波动
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
            
            if side == 'LONG':
                unrealized_profit = (self.current_price - entry_price) * quantity
            else:  # SHORT
                unrealized_profit = (entry_price - self.current_price) * quantity
            
            total_unrealized_profit += unrealized_profit
            
            positions.append({
                'symbol': symbol,
                'positionAmt': str(quantity),
                'entryPrice': str(entry_price),
                'unRealizedProfit': str(unrealized_profit),
                'leverage': str(self.config['trading']['leverage']),
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
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """获取模拟持仓信息"""
        account_info = await self.get_account_info()
        return account_info['positions']
    
    async def get_ticker_price(self, symbol: str) -> Dict[str, Any]:
        """获取模拟价格"""
        self._update_price()
        
        return {
            'symbol': symbol,
            'price': str(self.current_price),
            'time': int(time.time() * 1000)
        }
    
    async def get_klines(self, symbol: str, interval: str, 
                       limit: int = 1000, **kwargs) -> List[List[Any]]:
        """获取模拟K线数据"""
        if not self.price_history:
            self._generate_price_history()
        
        # 返回指定数量的K线数据
        recent_data = self.price_history[-limit:] if limit < len(self.price_history) else self.price_history
        
        klines = []
        for data in recent_data:
            klines.append([
                data['timestamp'] * 1000,  # open time
                str(data['open']),         # open
                str(data['high']),         # high
                str(data['low']),          # low
                str(data['close']),        # close
                str(data['volume']),       # volume
                data['timestamp'] * 1000 + 300000,  # close time
                '0',                       # quote asset volume
                0,                         # number of trades
                '0',                       # taker buy base asset volume
                '0',                       # taker buy quote asset volume
                '0'                        # ignore
            ])
        
        return klines
    
    async def create_order(self, symbol: str, side: str, order_type: str,
                         quantity: float, **kwargs) -> Dict[str, Any]:
        """创建模拟订单"""
        if not self.initialized:
            await self.initialize()
        
        self._update_price()
        
        # 计算订单价值
        leverage = self.config['trading']['leverage']
        order_value = quantity * self.current_price * leverage
        
        # 检查资金是否足够
        if order_value > self.available_balance:
            raise Exception("资金不足")
        
        # 生成订单ID
        order_id = int(time.time() * 1000)
        
        # 记录订单
        order = {
            'orderId': order_id,
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': quantity,
            'price': self.current_price,
            'status': 'FILLED',
            'executedQty': quantity,
            'cummulativeQuoteQty': order_value,
            'time': int(time.time() * 1000)
        }
        
        self.order_history.append(order)
        
        # 更新持仓
        if symbol not in self.positions:
            self.positions[symbol] = {
                'quantity': 0.0,
                'entry_price': 0.0,
                'side': None
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
        
        # 记录交易
        trade = {
            'timestamp': time.time(),
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': self.current_price,
            'order_id': order_id,
            'fee': order_value * self.config['fees']['taker']
        }
        self.trade_history.append(trade)
        
        self.logger.info(f"模拟订单执行: {side} {quantity} {symbol} @ {self.current_price}")
        
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


async def test_simulated_trading():
    """测试模拟交易功能"""
    try:
        # 加载配置
        config_loader = ConfigLoader()
        
        # 初始化模拟客户端
        client = SimulatedBinanceClient(config_loader)
        await client.initialize()
        
        logger.info("=" * 60)
        logger.info("开始测试模拟交易系统")
        logger.info("=" * 60)
        
        # 测试1: 获取账户信息
        logger.info("测试1: 获取账户信息...")
        account_info = await client.get_account_info()
        logger.info(f"初始资金: {account_info['totalWalletBalance']} USDT")
        logger.info(f"可用资金: {account_info['availableBalance']} USDT")
        
        # 测试2: 获取价格
        logger.info("测试2: 获取当前价格...")
        symbol = config_loader.get_config()['trading']['symbol']
        ticker = await client.get_ticker_price(symbol)
        logger.info(f"{symbol} 当前价格: {ticker['price']}")
        
        # 测试3: 获取K线数据
        logger.info("测试3: 获取K线数据...")
        klines = await client.get_klines(symbol, "5m", limit=5)
        logger.info(f"获取到 {len(klines)} 条K线数据")
        
        # 测试4: 执行买入订单
        logger.info("测试4: 执行模拟买入订单...")
        try:
            buy_order = await client.create_order(
                symbol=symbol,
                side="BUY",
                order_type="MARKET",
                quantity=0.01  # 0.01 BTC
            )
            logger.info(f"买入订单执行成功! 订单ID: {buy_order['orderId']}")
        except Exception as e:
            logger.error(f"买入订单失败: {e}")
        
        # 测试5: 查看持仓
        logger.info("测试5: 查看当前持仓...")
        positions = await client.get_positions()
        if positions:
            for pos in positions:
                if float(pos['positionAmt']) != 0:
                    logger.info(f"持仓: {pos['symbol']} {pos['positionAmt']} (盈亏: {pos['unRealizedProfit']})")
        else:
            logger.info("当前无持仓")
        
        # 测试6: 查看更新后的账户信息
        logger.info("测试6: 查看更新后的账户信息...")
        updated_account = await client.get_account_info()
        logger.info(f"更新后资金: {updated_account['totalWalletBalance']} USDT")
        logger.info(f"更新后可用: {updated_account['availableBalance']} USDT")
        logger.info(f"浮动盈亏: {updated_account['totalUnrealizedProfit']} USDT")
        
        # 测试7: 执行卖出订单（平仓）
        logger.info("测试7: 执行模拟卖出订单（平仓）...")
        try:
            sell_order = await client.create_order(
                symbol=symbol,
                side="SELL",
                order_type="MARKET",
                quantity=0.01  # 平掉0.01 BTC
            )
            logger.info(f"卖出订单执行成功! 订单ID: {sell_order['orderId']}")
        except Exception as e:
            logger.error(f"卖出订单失败: {e}")
        
        # 测试8: 查看最终账户状态
        logger.info("测试8: 查看最终账户状态...")
        final_account = await client.get_account_info()
        logger.info(f"最终资金: {final_account['totalWalletBalance']} USDT")
        logger.info(f"最终可用: {final_account['availableBalance']} USDT")
        
        # 测试9: 查看交易历史
        logger.info("测试9: 查看交易历史...")
        logger.info(f"总共执行了 {len(client.trade_history)} 笔交易")
        for i, trade in enumerate(client.trade_history[-2:], 1):
            logger.info(f"交易{i}: {trade['side']} {trade['quantity']} {trade['symbol']} @ {trade['price']}")
        
        logger.info("=" * 60)
        logger.info("模拟交易测试完成!")
        logger.info("=" * 60)
        
        # 关闭连接
        await client.close()
        
        return True
        
    except Exception as e:
        logger.error(f"模拟交易测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def main():
    """主函数"""
    print("=" * 60)
    print("模拟交易系统")
    print("=" * 60)
    print("特点:")
    print("✅ 完全模拟交易，无需API密钥")
    print("✅ 初始资金: 1000 USDT")
    print("✅ 实时价格模拟")
    print("✅ 完整的交易记录和持仓管理")
    print("✅ 手续费计算")
    print("✅ 浮动盈亏计算")
    print("=" * 60)
    
    success = asyncio.run(test_simulated_trading())
    
    if success:
        print("\n✅ 模拟交易测试成功!")
        print("\n下一步操作:")
        print("1. 修改 config.jsonc 中的交易策略参数")
        print("2. 运行: python run.py --mode bot (启动模拟交易机器人)")
        print("3. 运行: python run.py --mode web (启动Web界面)")
        print("4. 访问 http://localhost:8001 查看交易状态")
    else:
        print("\n❌ 模拟交易测试失败")


if __name__ == "__main__":
    main()