"""
配置文件加载模块
负责加载和验证交易系统的配置参数
"""

import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigLoader:
    """配置加载器类，负责加载和验证配置文件"""
    
    def __init__(self, config_path: str = "config.jsonc"):
        """
        初始化配置加载器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.config: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
    
    def load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            Dict[str, Any]: 配置字典
        
        Raises:
            FileNotFoundError: 配置文件不存在
            json.JSONDecodeError: JSON格式错误
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        
        try:
            # 读取文件内容并移除注释（JSONC格式支持）
            content = self.config_path.read_text(encoding='utf-8')
            # 移除单行注释
            lines = []
            for line in content.split('\n'):
                # 移除行内注释
                if '//' in line:
                    line = line.split('//')[0]
                lines.append(line)
            
            cleaned_content = '\n'.join(lines)
            self.config = json.loads(cleaned_content)
            
            self.logger.info("配置文件加载成功")
            return self.config
            
        except json.JSONDecodeError as e:
            self.logger.error(f"配置文件JSON格式错误: {e}")
            raise
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {e}")
            raise
    
    def validate_config(self) -> bool:
        """
        验证配置参数的完整性和有效性
        
        Returns:
            bool: 配置是否有效
        """
        if not self.config:
            self.logger.error("配置未加载，请先调用load_config()")
            return False
        
        required_sections = [
            'binance', 'trading', 'kline', 'indicators', 
            'strategy', 'risk_management', 'fees'
        ]
        
        # 检查必需配置节
        for section in required_sections:
            if section not in self.config:
                self.logger.error(f"缺少必需配置节: {section}")
                return False
        
        # 验证币安API配置
        binance_config = self.config['binance']
        required_binance_keys = ['api_key', 'api_secret']
        for key in required_binance_keys:
            if key not in binance_config or not binance_config[key]:
                self.logger.warning(f"币安API {key} 未配置，将无法进行实盘交易")
        
        # 验证交易配置
        trading_config = self.config['trading']
        if trading_config['leverage'] > 20:
            self.logger.warning("杠杆倍数过高，建议控制在10倍以内以降低风险")
        
        # 验证风险管理配置
        risk_config = self.config['risk_management']
        if risk_config['max_drawdown'] > 0.2:
            self.logger.warning("最大回撤限制设置过高，建议控制在10%以内")
        
        # 验证手续费配置
        fees_config = self.config['fees']
        if fees_config['maker'] <= 0 or fees_config['taker'] <= 0:
            self.logger.error("手续费率必须大于0")
            return False
        
        self.logger.info("配置验证通过")
        return True
    
    def get_config(self, section: Optional[str] = None, key: Optional[str] = None) -> Any:
        """
        获取配置值
        
        Args:
            section: 配置节名称
            key: 配置键名称
            
        Returns:
            Any: 配置值，如果未找到返回None
        """
        if not self.config:
            self.logger.warning("配置未加载，返回空值")
            return None
        
        if section is None:
            return self.config
        
        if section not in self.config:
            self.logger.warning(f"配置节不存在: {section}")
            return None
        
        if key is None:
            return self.config[section]
        
        if key not in self.config[section]:
            self.logger.warning(f"配置键不存在: {section}.{key}")
            return None
        
        return self.config[section][key]
    
    def update_config(self, section: str, key: str, value: Any) -> bool:
        """
        更新配置值
        
        Args:
            section: 配置节名称
            key: 配置键名称
            value: 新的配置值
            
        Returns:
            bool: 更新是否成功
        """
        if not self.config:
            self.logger.error("配置未加载，无法更新")
            return False
        
        if section not in self.config:
            self.logger.error(f"配置节不存在: {section}")
            return False
        
        self.config[section][key] = value
        self.logger.info(f"配置已更新: {section}.{key} = {value}")
        return True
    
    def save_config(self) -> bool:
        """
        保存配置到文件
        
        Returns:
            bool: 保存是否成功
        """
        if not self.config:
            self.logger.error("配置未加载，无法保存")
            return False
        
        try:
            # 使用缩进格式化JSON
            formatted_json = json.dumps(self.config, indent=2, ensure_ascii=False)
            self.config_path.write_text(formatted_json, encoding='utf-8')
            self.logger.info("配置文件保存成功")
            return True
        except Exception as e:
            self.logger.error(f"保存配置文件失败: {e}")
            return False


def create_default_config() -> Dict[str, Any]:
    """
    创建默认配置
    
    Returns:
        Dict[str, Any]: 默认配置字典
    """
    return {
        "binance": {
            "api_key": "",
            "api_secret": "",
            "testnet": True,
            "base_url": "https://fapi.binance.com",
            "testnet_url": "https://testnet.binancefuture.com",
            "websocket_url": "wss://fstream.binance.com/ws",
            "testnet_websocket_url": "wss://stream.binancefuture.com/ws"
        },
        "trading": {
            "symbol": "BTCUSDT",
            "contract_type": "PERPETUAL",
            "leverage": 3,
            "position_mode": "BOTH",
            "margin_type": "ISOLATED"
        },
        "kline": {
            "interval_5m": "5m",
            "interval_15m": "15m",
            "limit": 1000,
            "update_interval": 30000
        },
        "indicators": {
            "macd": {
                "fast_period": 12,
                "slow_period": 26,
                "signal_period": 9,
                "threshold_buy": 0.2,
                "threshold_sell": -0.2
            },
            "rsi": {
                "period": 14,
                "overbought": 70,
                "oversold": 30,
                "neutral_upper": 60,
                "neutral_lower": 40
            },
            "bollinger": {
                "period": 20,
                "std_dev": 2,
                "band_width_threshold": 0.1,
                "position_threshold": 0.7
            }
        },
        "strategy": {
            "name": "MultiIndicatorReversal",
            "enabled": True,
            "long_entry": {
                "macd_bullish": True,
                "rsi_oversold": True,
                "bollinger_lower": True,
                "volume_increase": True
            },
            "long_exit": {
                "macd_bearish": True,
                "rsi_overbought": True,
                "bollinger_upper": True,
                "profit_target": 0.03,
                "stop_loss": -0.02
            },
            "short_entry": {
                "macd_bearish": True,
                "rsi_overbought": True,
                "bollinger_upper": True,
                "volume_increase": True
            },
            "short_exit": {
                "macd_bullish": True,
                "rsi_oversold": True,
                "bollinger_lower": True,
                "profit_target": 0.03,
                "stop_loss": -0.02
            },
            "filter": {
                "min_band_width": 0.05,
                "max_trade_frequency": 6,
                "min_trend_strength": 0.3,
                "volatility_threshold": 0.01
            }
        },
        "risk_management": {
            "max_drawdown": 0.1,
            "daily_max_loss": 0.05,
            "position_size": 0.1,
            "max_position_size": 0.3,
            "trailing_stop": 0.015,
            "hedging_enabled": False
        },
        "fees": {
            "maker": 0.00027,
            "taker": 0.0005,
            "funding_rate_interval": 8
        },
        "execution": {
            "order_type": "LIMIT",
            "time_in_force": "GTC",
            "price_precision": 2,
            "quantity_precision": 3,
            "slippage": 0.001,
            "requote_count": 3,
            "requote_delay": 1000
        },
        "monitoring": {
            "webserver_port": 8080,
            "webserver_host": "0.0.0.0",
            "log_level": "INFO",
            "log_file": "logs/trading.log",
            "performance_interval": 60,
            "health_check_interval": 30
        },
        "database": {
            "enabled": True,
            "type": "sqlite",
            "path": "data/trading.db",
            "backup_interval": 3600,
            "retention_days": 30
        },
        "notifications": {
            "email_enabled": False,
            "email_server": "smtp.gmail.com",
            "email_port": 587,
            "email_username": "",
            "email_password": "",
            "telegram_enabled": False,
            "telegram_bot_token": "",
            "telegram_chat_id": ""
        },
        "system": {
            "loop_interval": 5,
            "timeout": 30,
            "retry_count": 3,
            "heartbeat_interval": 10,
            "shutdown_timeout": 60
        }
    }