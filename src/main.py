"""
自动交易系统主程序
整合所有组件并提供Web界面
"""

import asyncio
import time
import logging
from typing import Dict, Any
from datetime import datetime

from .config_loader import ConfigLoader
from .trading_engine import TradingEngine


class TradingBot:
    """自动交易机器人主类"""
    
    def __init__(self):
        """初始化交易机器人"""
        # 设置日志
        self.setup_logging()
        
        self.logger = logging.getLogger(__name__)
        self.config_loader = ConfigLoader()
        self.trading_engine = TradingEngine(self.config_loader)
        
        # 运行状态
        self.is_running = False
        self.start_time = None
        
    def setup_logging(self):
        """设置日志配置"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/trading_bot.log'),
                logging.StreamHandler()
            ]
        )
    
    async def initialize(self):
        """初始化交易系统"""
        try:
            self.logger.info("正在初始化交易系统...")
            
            # 加载配置
            self.config_loader.load_config()
            
            # 初始化交易引擎
            await self.trading_engine.initialize()
            
            self.logger.info("交易系统初始化完成")
            return True
            
        except Exception as e:
            self.logger.error(f"交易系统初始化失败: {e}")
            return False
    
    async def start(self):
        """启动交易系统"""
        if self.is_running:
            self.logger.warning("交易系统已经在运行中")
            return
        
        initialization_success = await self.initialize()
        if not initialization_success:
            self.logger.error("初始化失败，无法启动交易系统")
            return
        
        self.is_running = True
        self.start_time = time.time()
        self.logger.info("交易系统已启动")
        
        # 启动交易循环
        await self.run_trading_loop()
    
    async def stop(self):
        """停止交易系统"""
        if not self.is_running:
            self.logger.warning("交易系统未在运行")
            return
        
        self.is_running = False
        
        # 关闭交易引擎
        await self.trading_engine.close()
        
        # 平掉所有仓位
        await self.trading_engine.close_all_positions()
        
        runtime = time.time() - self.start_time
        self.logger.info(f"交易系统已停止，运行时间: {runtime:.2f}秒")
    
    async def run_trading_loop(self):
        """运行交易主循环"""
        config = self.config_loader.get_config()
        execution_config = config['execution']
        
        cycle_interval = execution_config['cycle_interval']
        
        self.logger.info(f"开始交易循环，间隔: {cycle_interval}秒")
        
        while self.is_running:
            try:
                # 执行交易周期
                await self.trading_engine.run_trading_cycle()
                
                # 监控风险
                risk_ok = await self.trading_engine.monitor_risk()
                if not risk_ok:
                    self.logger.critical("风险监控失败，停止交易")
                    await self.stop()
                    break
                
                # 等待下一个周期
                await asyncio.sleep(cycle_interval)
                
            except asyncio.CancelledError:
                self.logger.info("交易循环被取消")
                break
            except Exception as e:
                self.logger.error(f"交易循环执行错误: {e}")
                # 短暂等待后继续
                await asyncio.sleep(5)
    
    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        if not self.is_running:
            return {
                'status': 'stopped',
                'message': '交易系统未运行'
            }
        
        runtime = time.time() - self.start_time
        stats = self.trading_engine.get_trading_stats()
        
        return {
            'status': 'running',
            'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
            'runtime': runtime,
            'current_position': self.trading_engine.current_position,
            'account_balance': self.trading_engine.account_balance,
            'equity_value': self.trading_engine.equity_value,
            'max_drawdown': self.trading_engine.max_drawdown,
            'trading_stats': stats,
            'total_trades': self.trading_engine.total_trades,
            'config': self.config_loader.get_config()
        }
    
    def get_trade_history(self, limit: int = 50) -> list:
        """获取交易历史"""
        if limit <= 0:
            return self.trading_engine.trade_history
        return self.trading_engine.trade_history[-limit:]


# 全局交易机器人实例
trading_bot = None


def get_trading_bot() -> TradingBot:
    """获取交易机器人实例"""
    global trading_bot
    if trading_bot is None:
        trading_bot = TradingBot()
        # 立即加载配置，避免在多线程环境下配置未加载的问题
        try:
            trading_bot.config_loader.load_config()
        except Exception as e:
            logging.getLogger(__name__).warning(f"配置加载失败: {e}")
    return trading_bot


async def main():
    """主函数"""
    bot = get_trading_bot()
    
    try:
        # 启动交易系统
        await bot.start()
        
        # 保持运行（实际中应该由Web界面控制）
        while bot.is_running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n接收到中断信号，正在停止交易系统...")
        await bot.stop()
    except Exception as e:
        print(f"程序运行错误: {e}")
        await bot.stop()


if __name__ == "__main__":
    # 运行主程序
    asyncio.run(main())