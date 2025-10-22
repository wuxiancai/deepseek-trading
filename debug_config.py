#!/usr/bin/env python3

import json

def check_config():
    try:
        with open('config.jsonc', 'r', encoding='utf-8') as f:
            content = f.read()
            
        print("配置文件内容长度:", len(content))
        
        # 检查第14行
        lines = content.split('\n')
        if len(lines) >= 14:
            line14 = lines[13]  # 第14行（0-based索引13）
            print("第14行内容:", repr(line14))
            print("第14行长度:", len(line14))
            
            if len(line14) >= 24:
                char_at_24 = line14[23]  # 第24个字符（0-based索引23）
                print("第24个字符:", repr(char_at_24))
                print("字符编码:", ord(char_at_24))
        
        # 尝试解析JSON
        config = json.loads(content)
        print("✅ 配置文件JSON格式正确")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON解析错误: {e}")
        print(f"错误位置: {e.pos}")
        print(f"错误行: {e.lineno}")
        print(f"错误列: {e.colno}")
        
        # 显示错误位置附近的字符
        if hasattr(e, 'pos') and e.pos < len(content):
            start = max(0, e.pos - 10)
            end = min(len(content), e.pos + 10)
            print(f"错误位置附近的字符: {repr(content[start:end])}")
        
        return False
    except Exception as e:
        print(f"❌ 其他错误: {e}")
        return False

if __name__ == "__main__":
    check_config()