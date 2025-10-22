#!/bin/bash

# 同时启动交易机器人和Web服务器
source venv/bin/activate
python run.py --mode both --host 0.0.0.0 --port 8001 --log-level INFO
