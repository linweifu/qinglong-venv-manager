#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
.env 文件转换为青龙JSON格式工具
使用方法: python3 env-to-json.py input.env output.json
"""

import sys
import json
import re
import os

def parse_env_file(file_path):
    """解析 .env 文件"""
    envs = []
    
    if not os.path.exists(file_path):
        print(f"错误: 文件 {file_path} 不存在")
        return None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            
            # 跳过空行和注释
            if not line or line.startswith('#'):
                continue
            
            # 解析 KEY=VALUE 格式
            match = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$', line)
            if match:
                key = match.group(1)
                value = match.group(2)
                
                # 处理引号
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]
                
                # 处理转义字符
                value = value.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"').replace("\\'", "'")
                
                envs.append({
                    "name": key,
                    "value": value,
                    "remarks": f"从.env文件第{line_num}行导入"
                })
            else:
                print(f"警告: 第{line_num}行格式不正确，已跳过: {line}")
    
    return envs

def main():
    if len(sys.argv) != 3:
        print("使用方法: python3 env-to-json.py <输入.env文件> <输出JSON文件>")
        print("")
        print(".env文件格式示例:")
        print('ALI_NAME_LIST="幸卓账户,荣泰主账户,艾荣达账户,SAP账户,稍息账户,一诺康品"')
        print("API_KEY=your_api_key_here")
        print("SECRET_TOKEN='your_secret_token'")
        print("# 注释会被忽略")
        print("DEBUG=true")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    print("=== .env 文件转换工具 (Python版) ===")
    print(f"输入文件: {input_file}")
    print(f"输出文件: {output_file}")
    
    # 解析 .env 文件
    envs = parse_env_file(input_file)
    if envs is None:
        sys.exit(1)
    
    if not envs:
        print("警告: 没有找到有效的环境变量")
        sys.exit(1)
    
    # 生成JSON文件
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(envs, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 转换完成！")
        print(f"   共转换 {len(envs)} 个环境变量")
        print(f"   输出文件: {output_file}")
        print("")
        print("转换的环境变量:")
        for env in envs:
            value_preview = env['value'][:30] + '...' if len(env['value']) > 30 else env['value']
            print(f"  - {env['name']}: {value_preview}")
        print("")
        print("现在可以使用以下命令批量添加到青龙:")
        print(f"   bash batch-add-envs.sh {output_file}")
        
    except Exception as e:
        print(f"❌ 写入文件失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
