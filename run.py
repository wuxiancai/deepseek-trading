#!/usr/bin/env python3
"""
自动交易系统启动脚本
"""

import asyncio
import argparse
import logging
from pathlib import Path

from src.main import TradingBot
from src.web_server import WebServer


async def run_trading_bot():
    """运行交易机器人"""
    bot = TradingBot()
    
    try:
        # 初始化交易系统
        success = await bot.initialize()
        if not success:
            logging.error("交易系统初始化失败")
            return
        
        # 启动交易系统
        await bot.start()
        
        # 保持运行
        while bot.is_running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n接收到中断信号，正在停止交易系统...")
        await bot.stop()
    except Exception as e:
        logging.error(f"程序运行错误: {e}")
        await bot.stop()


def run_web_server():
    """运行Web服务器"""
    server = WebServer()
    server.run()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='币安自动交易系统')
    parser.add_argument('--mode', choices=['bot', 'web', 'both'], default='both',
                       help='运行模式: bot(仅交易), web(仅Web), both(两者)')
    parser.add_argument('--host', default='0.0.0.0', help='Web服务器主机地址')
    parser.add_argument('--port', type=int, default=8000, help='Web服务器端口')
    parser.add_argument('--log-level', default='INFO', 
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                       help='日志级别')
    
    args = parser.parse_args()
    
    # 设置日志
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/trading_system.log'),
            logging.StreamHandler()
        ]
    )
    
    # 创建必要的目录
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    
    if args.mode == 'bot':
        # 仅运行交易机器人
        asyncio.run(run_trading_bot())
    elif args.mode == 'web':
        # 仅运行Web服务器
        run_web_server()
    else:
        # 同时运行两者
        import threading
        
        def run_bot():
            asyncio.run(run_trading_bot())
        
        def run_web():
            server = WebServer()
            server.run(host=args.host, port=args.port)
        
        # 启动Web服务器线程
        web_thread = threading.Thread(target=run_web, daemon=True)
        web_thread.start()
        
        # 在主线程运行交易机器人
        run_bot()


if __name__ == "__main__":
    main()