"""
技术指标计算模块
包含MACD、RSI、布林带等常用技术指标的计算
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
import logging


class TechnicalIndicators:
    """技术指标计算类"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_macd(self, close_prices: List[float], 
                      fast_period: int = 12, 
                      slow_period: int = 26, 
                      signal_period: int = 9) -> Dict[str, List[float]]:
        """
        计算MACD指标
        
        Args:
            close_prices: 收盘价列表
            fast_period: 快线周期
            slow_period: 慢线周期
            signal_period: 信号线周期
            
        Returns:
            Dict[str, List[float]]: MACD指标数据
        """
        if len(close_prices) < slow_period + signal_period:
            self.logger.warning("数据长度不足，无法计算MACD")
            return {
                'macd': [0] * len(close_prices),
                'signal': [0] * len(close_prices),
                'histogram': [0] * len(close_prices)
            }
        
        # 转换为pandas Series
        close_series = pd.Series(close_prices)
        
        # 计算EMA
        ema_fast = close_series.ewm(span=fast_period, adjust=False).mean()
        ema_slow = close_series.ewm(span=slow_period, adjust=False).mean()
        
        # 计算MACD线
        macd_line = ema_fast - ema_slow
        
        # 计算信号线
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        
        # 计算柱状图
        histogram = macd_line - signal_line
        
        return {
            'macd': macd_line.tolist(),
            'signal': signal_line.tolist(),
            'histogram': histogram.tolist()
        }
    
    def calculate_rsi(self, close_prices: List[float], period: int = 14) -> List[float]:
        """
        计算RSI指标
        
        Args:
            close_prices: 收盘价列表
            period: RSI周期
            
        Returns:
            List[float]: RSI值列表
        """
        if len(close_prices) < period + 1:
            self.logger.warning("数据长度不足，无法计算RSI")
            return [50] * len(close_prices)  # 返回中性值
        
        # 计算价格变化
        close_series = pd.Series(close_prices)
        delta = close_series.diff()
        
        # 分离上涨和下跌
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # 计算平均增益和平均损失
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # 处理初始值
        avg_gain.iloc[period-1] = gain.iloc[1:period+1].mean()
        avg_loss.iloc[period-1] = loss.iloc[1:period+1].mean()
        
        # 计算RS
        rs = avg_gain / avg_loss
        
        # 计算RSI
        rsi = 100 - (100 / (1 + rs))
        
        # 填充前period个值为50
        rsi.iloc[:period] = 50
        
        return rsi.fillna(50).tolist()
    
    def calculate_bollinger_bands(self, close_prices: List[float], 
                                period: int = 20, 
                                std_dev: float = 2.0) -> Dict[str, List[float]]:
        """
        计算布林带指标
        
        Args:
            close_prices: 收盘价列表
            period: 移动平均周期
            std_dev: 标准差倍数
            
        Returns:
            Dict[str, List[float]]: 布林带数据
        """
        if len(close_prices) < period:
            self.logger.warning("数据长度不足，无法计算布林带")
            return {
                'middle': close_prices.copy(),
                'upper': close_prices.copy(),
                'lower': close_prices.copy(),
                'bandwidth': [0] * len(close_prices),
                'percent_b': [0.5] * len(close_prices)
            }
        
        close_series = pd.Series(close_prices)
        
        # 计算中轨（移动平均）
        middle_band = close_series.rolling(window=period).mean()
        
        # 计算标准差
        std = close_series.rolling(window=period).std()
        
        # 计算上轨和下轨
        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)
        
        # 计算带宽
        bandwidth = ((upper_band - lower_band) / middle_band) * 100
        
        # 计算%b指标
        percent_b = (close_series - lower_band) / (upper_band - lower_band)
        
        # 填充前period-1个值
        middle_band.iloc[:period-1] = close_series.iloc[:period-1]
        upper_band.iloc[:period-1] = close_series.iloc[:period-1]
        lower_band.iloc[:period-1] = close_series.iloc[:period-1]
        bandwidth.iloc[:period-1] = 0
        percent_b.iloc[:period-1] = 0.5
        
        return {
            'middle': middle_band.tolist(),
            'upper': upper_band.tolist(),
            'lower': lower_band.tolist(),
            'bandwidth': bandwidth.tolist(),
            'percent_b': percent_b.tolist()
        }
    
    def calculate_ma(self, close_prices: List[float], period: int) -> List[float]:
        """
        计算移动平均线
        
        Args:
            close_prices: 收盘价列表
            period: 移动平均周期
            
        Returns:
            List[float]: 移动平均值列表
        """
        if len(close_prices) < period:
            self.logger.warning(f"数据长度不足，无法计算{period}周期MA")
            return close_prices.copy()
        
        close_series = pd.Series(close_prices)
        ma = close_series.rolling(window=period).mean()
        
        # 填充前period-1个值为第一个有效值
        ma.iloc[:period-1] = close_series.iloc[:period-1]
        
        return ma.tolist()
    
    def calculate_ema(self, close_prices: List[float], period: int) -> List[float]:
        """
        计算指数移动平均线
        
        Args:
            close_prices: 收盘价列表
            period: EMA周期
            
        Returns:
            List[float]: EMA值列表
        """
        if len(close_prices) < period:
            self.logger.warning(f"数据长度不足，无法计算{period}周期EMA")
            return close_prices.copy()
        
        close_series = pd.Series(close_prices)
        ema = close_series.ewm(span=period, adjust=False).mean()
        
        return ema.tolist()
    
    def calculate_atr(self, high_prices: List[float], 
                     low_prices: List[float], 
                     close_prices: List[float], 
                     period: int = 14) -> List[float]:
        """
        计算平均真实波幅(ATR)
        
        Args:
            high_prices: 最高价列表
            low_prices: 最低价列表
            close_prices: 收盘价列表
            period: ATR周期
            
        Returns:
            List[float]: ATR值列表
        """
        if len(high_prices) < period or len(low_prices) < period or len(close_prices) < period:
            self.logger.warning("数据长度不足，无法计算ATR")
            return [0] * len(close_prices)
        
        high_series = pd.Series(high_prices)
        low_series = pd.Series(low_prices)
        close_series = pd.Series(close_prices)
        
        # 计算真实波幅
        tr1 = high_series - low_series
        tr2 = abs(high_series - close_series.shift(1))
        tr3 = abs(low_series - close_series.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        # 计算ATR
        atr = tr.rolling(window=period).mean()
        
        # 填充前period-1个值为第一个有效值
        atr.iloc[:period-1] = tr.iloc[:period-1]
        
        return atr.tolist()
    
    def calculate_volume_indicators(self, volumes: List[float], 
                                  close_prices: List[float], 
                                  period: int = 20) -> Dict[str, List[float]]:
        """
        计算成交量相关指标
        
        Args:
            volumes: 成交量列表
            close_prices: 收盘价列表
            period: 计算周期
            
        Returns:
            Dict[str, List[float]]: 成交量指标数据
        """
        if len(volumes) < period:
            self.logger.warning("数据长度不足，无法计算成交量指标")
            return {
                'volume_ma': volumes.copy(),
                'obv': [0] * len(volumes),
                'vpt': [0] * len(volumes)
            }
        
        volume_series = pd.Series(volumes)
        close_series = pd.Series(close_prices)
        
        # 成交量移动平均
        volume_ma = volume_series.rolling(window=period).mean()
        
        # 能量潮(OBV)
        price_change = close_series.diff()
        obv = volume_series.copy()
        obv[price_change < 0] = -obv[price_change < 0]
        obv = obv.cumsum()
        
        # 量价趋势(VPT)
        vpt = volume_series * ((close_series - close_series.shift(1)) / close_series.shift(1))
        vpt = vpt.cumsum()
        
        # 填充初始值
        volume_ma.iloc[:period-1] = volume_series.iloc[:period-1]
        obv.iloc[0] = 0
        vpt.iloc[0] = 0
        
        return {
            'volume_ma': volume_ma.tolist(),
            'obv': obv.tolist(),
            'vpt': vpt.tolist()
        }
    
    def detect_trend(self, close_prices: List[float], 
                    short_period: int = 20, 
                    long_period: int = 50) -> str:
        """
        检测趋势方向
        
        Args:
            close_prices: 收盘价列表
            short_period: 短期均线周期
            long_period: 长期均线周期
            
        Returns:
            str: 趋势方向 ('uptrend', 'downtrend', 'sideways')
        """
        if len(close_prices) < long_period:
            return 'sideways'
        
        # 计算短期和长期均线
        short_ma = self.calculate_ma(close_prices, short_period)
        long_ma = self.calculate_ma(close_prices, long_period)
        
        # 获取最新值
        latest_short = short_ma[-1]
        latest_long = long_ma[-1]
        
        # 判断趋势
        if latest_short > latest_long * 1.01:  # 短期均线高于长期均线1%
            return 'uptrend'
        elif latest_short < latest_long * 0.99:  # 短期均线低于长期均线1%
            return 'downtrend'
        else:
            return 'sideways'
    
    def detect_oscillation(self, close_prices: List[float], 
                         bollinger_period: int = 20, 
                         bollinger_std: float = 2.0,
                         atr_period: int = 14) -> bool:
        """
        检测市场是否处于震荡状态
        
        Args:
            close_prices: 收盘价列表
            bollinger_period: 布林带周期
            bollinger_std: 布林带标准差
            atr_period: ATR周期
            
        Returns:
            bool: 是否处于震荡状态
        """
        if len(close_prices) < max(bollinger_period, atr_period):
            return False
        
        # 计算布林带
        bollinger = self.calculate_bollinger_bands(close_prices, bollinger_period, bollinger_std)
        
        # 计算ATR
        # 这里简化处理，实际需要最高价和最低价数据
        atr_values = self.calculate_atr(close_prices, close_prices, close_prices, atr_period)
        
        # 获取最新值
        latest_bandwidth = bollinger['bandwidth'][-1]
        latest_atr = atr_values[-1]
        latest_close = close_prices[-1]
        
        # 判断震荡条件
        # 1. 布林带带宽较小（小于2%）
        # 2. ATR相对价格比例较小（小于1%）
        bandwidth_condition = latest_bandwidth < 2.0
        atr_condition = (latest_atr / latest_close) < 0.01
        
        return bandwidth_condition and atr_condition
    
    def generate_signals(self, close_prices: List[float], 
                        indicators_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成交易信号
        
        Args:
            close_prices: 收盘价列表
            indicators_config: 指标配置
            
        Returns:
            Dict[str, Any]: 交易信号和指标数据
        """
        signals = {
            'macd_signal': 'hold',
            'rsi_signal': 'hold', 
            'bollinger_signal': 'hold',
            'trend': 'sideways',
            'is_oscillating': False,
            'overall_signal': 'hold'
        }
        
        # 获取配置参数
        macd_config = indicators_config['macd']
        rsi_config = indicators_config['rsi']
        bollinger_config = indicators_config['bollinger']
        
        # 计算各项指标
        macd_data = self.calculate_macd(
            close_prices, 
            macd_config['fast_period'], 
            macd_config['slow_period'], 
            macd_config['signal_period']
        )
        
        rsi_values = self.calculate_rsi(close_prices, rsi_config['period'])
        
        bollinger_data = self.calculate_bollinger_bands(
            close_prices, 
            bollinger_config['period'], 
            bollinger_config['std_dev']
        )
        
        # 检测趋势
        trend = self.detect_trend(close_prices)
        
        # 检测震荡
        is_oscillating = self.detect_oscillation(close_prices)
        
        # 生成MACD信号
        if len(macd_data['macd']) >= 2:
            latest_macd = macd_data['macd'][-1]
            latest_signal = macd_data['signal'][-1]
            prev_macd = macd_data['macd'][-2]
            prev_signal = macd_data['signal'][-2]
            
            # 金叉信号
            if prev_macd <= prev_signal and latest_macd > latest_signal:
                signals['macd_signal'] = 'buy'
            # 死叉信号  
            elif prev_macd >= prev_signal and latest_macd < latest_signal:
                signals['macd_signal'] = 'sell'
        
        # 生成RSI信号
        if len(rsi_values) >= 1:
            latest_rsi = rsi_values[-1]
            
            if latest_rsi <= rsi_config['oversold']:
                signals['rsi_signal'] = 'buy'
            elif latest_rsi >= rsi_config['overbought']:
                signals['rsi_signal'] = 'sell'
        
        # 生成布林带信号
        if len(bollinger_data['percent_b']) >= 1:
            latest_pct_b = bollinger_data['percent_b'][-1]
            
            if latest_pct_b <= 0.2:  # 价格接近下轨
                signals['bollinger_signal'] = 'buy'
            elif latest_pct_b >= 0.8:  # 价格接近上轨
                signals['bollinger_signal'] = 'sell'
        
        # 综合信号判断
        signals['trend'] = trend
        signals['is_oscillating'] = is_oscillating
        
        # 综合所有信号生成最终信号
        buy_signals = [
            signals['macd_signal'] == 'buy',
            signals['rsi_signal'] == 'buy',
            signals['bollinger_signal'] == 'buy',
            trend == 'uptrend' or not is_oscillating
        ]
        
        sell_signals = [
            signals['macd_signal'] == 'sell',
            signals['rsi_signal'] == 'sell', 
            signals['bollinger_signal'] == 'sell',
            trend == 'downtrend' or not is_oscillating
        ]
        
        if sum(buy_signals) >= 2:  # 至少2个买入信号
            signals['overall_signal'] = 'buy'
        elif sum(sell_signals) >= 2:  # 至少2个卖出信号
            signals['overall_signal'] = 'sell'
        
        # 添加指标数据到返回结果
        signals.update({
            'macd_data': macd_data,
            'rsi_values': rsi_values,
            'bollinger_data': bollinger_data,
            'close_prices': close_prices
        })
        
        return signals