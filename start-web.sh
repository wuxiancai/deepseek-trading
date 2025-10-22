#!/bin/bash

# 启动Web服务器
source venv/bin/activate
python run.py --mode web --host 0.0.0.0 --port 8001 --log-level INFO
