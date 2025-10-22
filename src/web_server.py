"""
Web服务器
提供交易系统的Web界面和API接口
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
import uvicorn
import json
from typing import Dict, Any
from pathlib import Path

from .main import get_trading_bot


class WebServer:
    """Web服务器类"""
    
    def __init__(self):
        self.app = FastAPI(
            title="币安自动交易系统",
            description="基于币安API的自动化交易系统",
            version="1.0.0"
        )
        
        self.bot = get_trading_bot()
        
        # 设置模板和静态文件
        self.setup_static_files()
        self.setup_routes()
    
    def setup_static_files(self):
        """设置静态文件服务"""
        # 创建静态文件目录
        static_dir = Path("static")
        static_dir.mkdir(exist_ok=True)
        
        # 挂载静态文件
        self.app.mount("/static", StaticFiles(directory="static"), name="static")
        
        # 设置模板
        templates_dir = Path("templates")
        templates_dir.mkdir(exist_ok=True)
        self.templates = Jinja2Templates(directory="templates")
    
    def setup_routes(self):
        """设置路由"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def read_root(request: Request):
            """主页"""
            return self.templates.TemplateResponse(
                "index.html", 
                {"request": request, "title": "币安自动交易系统"}
            )
        
        @self.app.get("/api/status")
        async def get_status() -> Dict[str, Any]:
            """获取系统状态"""
            return self.bot.get_status()
        
        @self.app.get("/api/trades")
        async def get_trades(limit: int = 50):
            """获取交易历史"""
            return self.bot.get_trade_history(limit)
        
        @self.app.post("/api/start")
        async def start_trading():
            """启动交易系统"""
            try:
                await self.bot.start()
                return {"status": "success", "message": "交易系统已启动"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/stop")
        async def stop_trading():
            """停止交易系统"""
            try:
                await self.bot.stop()
                return {"status": "success", "message": "交易系统已停止"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/config")
        async def get_config():
            """获取配置信息"""
            try:
                config = self.bot.config_loader.get_config()
                return config
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/health")
        async def health_check():
            """健康检查"""
            return {"status": "healthy", "timestamp": time.time()}
    
    def run(self, host: str = "0.0.0.0", port: int = 5002):
        """运行Web服务器"""
        uvicorn.run(self.app, host=host, port=port)


# 全局Web服务器实例
web_server = None


def get_web_server() -> WebServer:
    """获取Web服务器实例"""
    global web_server
    if web_server is None:
        web_server = WebServer()
    return web_server


if __name__ == "__main__":
    server = get_web_server()
    server.run()