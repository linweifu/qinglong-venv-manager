#!/bin/bash

# =============================================================================
# 青龙虚拟环境管理器 - 一键安装脚本
# =============================================================================
# 
# 🚀 为青龙面板提供完全自动化的虚拟环境管理解决方案
# 
# ✨ 特性:
#   - 零配置：安装后即可使用，无需任何配置
#   - 自动创建：订阅更新时自动创建虚拟环境  
#   - 自动激活：Python 脚本执行时自动激活虚拟环境
#   - 完全隔离：每个项目独立的依赖环境
# 
# 🎯 使用方法:
#   bash qinglong_venv_installer.sh            # 快速安装（推荐）
#   bash qinglong_venv_installer.sh install    # 完整安装
#   bash qinglong_venv_installer.sh uninstall  # 卸载系统
#   bash qinglong_venv_installer.sh status     # 查看状态
#   bash qinglong_venv_installer.sh repair     # 修复安装
#
# =============================================================================

# 配置变量
SITECUSTOMIZE_FILE="/ql/shell/preload/sitecustomize.py"
SUBSCRIPTION_SERVICE_FILE="/ql/back/services/subscription.ts"
BACKUP_DIR="/ql/data/backup/qinglong_venv"
SCRIPTS_DIR="/ql/scripts"
MANAGER_SCRIPT="$SCRIPTS_DIR/qinglong_venv_manager.py"
AUTO_VENV_SCRIPT="$SCRIPTS_DIR/auto_create_venv.py"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

# 日志函数
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_debug() { echo -e "${PURPLE}[DEBUG]${NC} $1"; }

# 显示标题
show_banner() {
    echo -e "${CYAN}"
    echo "============================================================================="
    echo "                    🚀 青龙虚拟环境管理器"
    echo "============================================================================="
    echo -e "${NC}"
    echo "✨ 零配置、自动创建、自动激活、完全隔离"
    echo "🎯 让虚拟环境管理变得简单、自动、可靠！"
    echo "📦 版本: 1.0.0"
    echo
}

# 检查环境
check_environment() {
    log_info "检查运行环境..."
    
    # 检查是否在青龙环境中
    if [[ ! -f "$SITECUSTOMIZE_FILE" ]]; then
        log_error "未找到青龙 sitecustomize.py 文件"
        log_error "请确保在青龙容器中运行此脚本"
        exit 1
    fi
    
    if [[ ! -f "$SUBSCRIPTION_SERVICE_FILE" ]]; then
        log_error "未找到青龙订阅服务文件"
        log_error "请确保在青龙容器中运行此脚本"
        exit 1
    fi
    
    if [[ ! -d "/ql/data" ]]; then
        log_error "未找到青龙数据目录"
        exit 1
    fi
    
    # 检查权限
    if [[ $EUID -ne 0 ]]; then
        log_error "需要 root 权限运行此脚本"
        exit 1
    fi
    
    # 检查必要命令
    for cmd in python3 npm pm2; do
        if ! command -v $cmd &> /dev/null; then
            log_warning "$cmd 命令不存在，某些功能可能不可用"
        fi
    done
    
    log_success "环境检查通过"
}

# 创建备份
create_backup() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    mkdir -p "$BACKUP_DIR"
    
    log_info "创建备份..."
    
    # 备份 sitecustomize.py
    if [[ -f "$SITECUSTOMIZE_FILE" ]]; then
        cp "$SITECUSTOMIZE_FILE" "$BACKUP_DIR/sitecustomize.py.backup.$timestamp"
        log_success "已备份 sitecustomize.py"
    fi
    
    # 备份订阅服务
    if [[ -f "$SUBSCRIPTION_SERVICE_FILE" ]]; then
        cp "$SUBSCRIPTION_SERVICE_FILE" "$BACKUP_DIR/subscription.ts.backup.$timestamp"
        log_success "已备份 subscription.ts"
    fi
    
    # 记录备份信息
    echo "$timestamp" > "$BACKUP_DIR/latest_backup.txt"
    echo "sitecustomize.py.backup.$timestamp" >> "$BACKUP_DIR/backup_files.txt"
    echo "subscription.ts.backup.$timestamp" >> "$BACKUP_DIR/backup_files.txt"
    
    log_success "备份完成: $BACKUP_DIR"
}

# 安装 sitecustomize.py 补丁
install_sitecustomize_patch() {
    log_info "安装 sitecustomize.py 虚拟环境补丁..."
    
    cat > "$SITECUSTOMIZE_FILE" << 'EOF'
import os
import re
import subprocess
import json
import builtins
import sys
import env
import signal
from client import Client


def try_parse_int(value):
    try:
        return int(value)
    except ValueError:
        return None


def expand_range(range_str, max_value):
    temp_range_str = (
        range_str.strip()
        .replace("-max", f"-{max_value}")
        .replace("max-", f"{max_value}-")
    )

    result = []
    for part in temp_range_str.split(" "):
        range_match = re.match(r"^(\d+)([-~_])(\d+)$", part)
        if range_match:
            start, _, end = map(try_parse_int, range_match.groups())
            step = 1 if start < end else -1
            result.extend(range(start, end + step, step))
        else:
            result.append(int(part))

    return result


def auto_activate_venv_after_env_loaded():
    """
    在环境变量加载完成后自动激活虚拟环境
    
    检测逻辑:
    1. 从当前工作目录检测项目名称
    2. 从脚本路径检测项目名称  
    3. 向上查找包含 .venv 的目录
    
    激活逻辑:
    1. 查找项目的 .venv 目录
    2. 将 site-packages 添加到 sys.path
    3. 设置相关环境变量
    """
    try:
        # 获取当前工作目录和脚本路径
        current_dir = os.getcwd()
        script_file = sys.argv[0] if sys.argv else ""
        
        project_dir = None
        project_name = None
        
        # 方法1: 从当前工作目录检测项目
        if '/ql/data/scripts/' in current_dir:
            scripts_path = '/ql/data/scripts/'
            if current_dir.startswith(scripts_path):
                relative_path = current_dir[len(scripts_path):]
                if relative_path:
                    project_name = relative_path.split('/')[0]
                    project_dir = os.path.join(scripts_path, project_name)
        
        # 方法2: 从脚本路径检测项目
        if not project_dir and script_file and '/ql/data/scripts/' in script_file:
            scripts_path = '/ql/data/scripts/'
            if script_file.startswith(scripts_path):
                relative_path = script_file[len(scripts_path):]
                if relative_path:
                    project_name = relative_path.split('/')[0]
                    project_dir = os.path.join(scripts_path, project_name)
        
        # 方法3: 向上查找包含 .venv 的目录
        if not project_dir:
            check_dir = current_dir
            max_depth = 5  # 最多向上查找5级目录
            depth = 0
            
            while check_dir and check_dir != '/' and check_dir != '/ql' and depth < max_depth:
                if os.path.isdir(os.path.join(check_dir, '.venv')):
                    project_dir = check_dir
                    project_name = os.path.basename(check_dir)
                    break
                parent_dir = os.path.dirname(check_dir)
                if parent_dir == check_dir:  # 到达根目录
                    break
                check_dir = parent_dir
                depth += 1
        
        # 如果找到了项目目录，激活虚拟环境
        if project_dir and project_name:
            venv_dir = os.path.join(project_dir, '.venv')
            
            if os.path.isdir(venv_dir):
                # 检查多个可能的 Python 版本路径
                possible_site_packages = [
                    os.path.join(venv_dir, 'lib', 'python3.11', 'site-packages'),
                    os.path.join(venv_dir, 'lib', 'python3.10', 'site-packages'),
                    os.path.join(venv_dir, 'lib', 'python3.9', 'site-packages'),
                    os.path.join(venv_dir, 'lib', 'python3.12', 'site-packages'),
                    os.path.join(venv_dir, 'lib', 'python3.8', 'site-packages'),
                ]
                
                for site_packages in possible_site_packages:
                    if os.path.isdir(site_packages):
                        # 检查是否已经添加过
                        if site_packages not in sys.path:
                            # 将虚拟环境路径添加到 sys.path 的第二位（第一位是当前目录）
                            sys.path.insert(1, site_packages)
                            print(f"[VENV_AUTO] ✅ 已激活虚拟环境: {project_name}")
                            print(f"[VENV_AUTO] 虚拟环境路径: {site_packages}")
                            
                            # 设置环境变量
                            os.environ['VIRTUAL_ENV'] = venv_dir
                            os.environ['VIRTUAL_ENV_PROJECT'] = project_name
                            
                            return True
                        else:
                            # 已经激活过，静默返回
                            return True
                
                # 如果找到 .venv 目录但没有找到 site-packages
                # print(f"[VENV_AUTO] ⚠️  项目 {project_name} 的虚拟环境可能损坏")
        
        return False
        
    except Exception as e:
        # 静默处理异常，不影响正常的Python执行
        # print(f"[VENV_AUTO] 虚拟环境激活异常: {e}")
        return False


def run():
    try:
        prev_pythonpath = os.getenv("PREV_PYTHONPATH", "")
        os.environ["PYTHONPATH"] = prev_pythonpath

        split_str = "__sitecustomize__"
        file_name = sys.argv[0].replace(f"{os.getenv('dir_scripts')}/", "")
        
        # 创建临时文件路径
        temp_file = f"/tmp/env_{os.getpid()}.json"
        
        # 构建命令数组
        commands = [
            f'source {os.getenv("file_task_before")} {file_name}'
        ]
        
        task_before = os.getenv("task_before")
        if task_before:
            escaped_task_before = task_before.replace('"', '\\"').replace("$", "\\$")
            commands.append(f"eval '{escaped_task_before}'")
            print("执行前置命令\n")
            
        commands.append(f"echo -e '{split_str}'")
        
        # 修改 Python 命令，使用单行并正确处理引号
        python_cmd = f"python3 -c 'import os,json; f=open(\\\"{temp_file}\\\",\\\"w\\\"); json.dump(dict(os.environ),f); f.close()'"
        commands.append(python_cmd)
        
        command = " && ".join(cmd for cmd in commands if cmd)
        command = f'bash -c "{command}"'

        res = subprocess.check_output(command, shell=True, encoding="utf-8")
        output = res.split(split_str)[0]

        try:
            with open(temp_file, 'r') as f:
                env_json = json.loads(f.read())

            for key, value in env_json.items():
                os.environ[key] = value

            os.unlink(temp_file)
            
            # 🎯 关键：在环境变量加载完成后激活虚拟环境
            # 这确保了青龙的环境变量已经加载，虚拟环境可以正常访问
            auto_activate_venv_after_env_loaded()
            
        except Exception as json_error:
            print(f"⚠ Failed to parse environment variables: {json_error}")
            try:
                os.unlink(temp_file)
            except:
                pass

        if len(output) > 0:
            print(output)
        if task_before:
            print("执行前置命令结束\n")

    except subprocess.CalledProcessError as error:
        print(f"⚠ run task before error: {error}")
        if task_before:
            print("执行前置命令结束\n")
    except OSError as error:
        error_message = str(error)
        if "Argument list too long" not in error_message:
            print(f"⚠ run task before error: {error}")
        if task_before:
            print("执行前置命令结束\n")
    except Exception as error:
        print(f"⚠ run task before error: {error}")
        if task_before:
            print("执行前置命令结束\n")

    import task_before

    env_param = os.getenv("envParam")
    num_param = os.getenv("numParam")

    if env_param and num_param:
        array = (os.getenv(env_param) or "").split("&")
        run_arr = expand_range(num_param, len(array))
        array_run = [array[i - 1] for i in run_arr if i - 1 < len(array) and i > 0]
        env_str = "&".join(array_run)
        os.environ[env_param] = env_str


def handle_sigterm(signum, frame):
    sys.exit(15)


try:
    signal.signal(signal.SIGTERM, handle_sigterm)

    run()

    from __ql_notify__ import send

    class BaseApi(Client):
        def notify(self, *args, **kwargs):
            return send(*args, **kwargs)

    QLAPI = BaseApi()
    builtins.QLAPI = QLAPI
except Exception as error:
    print(f"run builtin code error: {error}\n")
EOF

    log_success "sitecustomize.py 补丁安装完成"
}

# 创建虚拟环境自动创建脚本
create_auto_venv_script() {
    log_info "创建虚拟环境自动创建脚本..."
    
    mkdir -p "$SCRIPTS_DIR"
    
    cat > "$AUTO_VENV_SCRIPT" << 'EOF'
#!/usr/bin/env python3
"""
青龙订阅虚拟环境自动创建脚本
在订阅更新后自动检测并创建虚拟环境
"""
import os
import sys
import subprocess
import json
from datetime import datetime
from pathlib import Path

def log(message):
    """带时间戳的日志输出"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [AUTO_VENV] {message}")

def detect_project_type(project_dir):
    """检测项目类型和依赖文件"""
    project_path = Path(project_dir)
    
    # Python 项目检测
    python_files = [
        "requirements.txt", "pyproject.toml", 
        "setup.py", "Pipfile"
    ]
    
    # Node.js 项目检测
    nodejs_files = [
        "package.json", "yarn.lock", "pnpm-lock.yaml"
    ]
    
    has_python = any((project_path / f).exists() for f in python_files)
    has_nodejs = any((project_path / f).exists() for f in nodejs_files)
    
    return {
        "has_python": has_python,
        "has_nodejs": has_nodejs,
        "python_deps": [str(project_path / f) for f in python_files if (project_path / f).exists()],
        "nodejs_deps": [str(project_path / f) for f in nodejs_files if (project_path / f).exists()]
    }

def create_python_venv(project_name, scripts_dir, repo_dir):
    """创建 Python 虚拟环境"""
    venv_dir = os.path.join(scripts_dir, ".venv")
    
    # 创建虚拟环境
    if not os.path.exists(venv_dir):
        log(f"为项目 {project_name} 创建 Python 虚拟环境...")
        result = subprocess.run([
            sys.executable, "-m", "venv", venv_dir
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            log(f"❌ Python 虚拟环境创建失败: {result.stderr}")
            return False
        log("✅ Python 虚拟环境创建成功")
    else:
        log("✅ Python 虚拟环境已存在")
    
    # 安装依赖
    pip_path = os.path.join(venv_dir, "bin", "pip")
    
    # 查找依赖文件
    requirements_files = [
        os.path.join(scripts_dir, "requirements.txt"),
        os.path.join(repo_dir, "requirements.txt"),
    ]
    
    for req_file in requirements_files:
        if os.path.exists(req_file):
            log(f"发现依赖文件: {req_file}")
            log("安装 Python 依赖...")
            
            result = subprocess.run([
                pip_path, "install", "-r", req_file,
                "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
                "--timeout", "300"
            ], capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                log("✅ Python 依赖安装成功")
            else:
                log(f"⚠️  Python 依赖安装失败: {result.stderr}")
            break
    else:
        log("⚠️  未找到 Python 依赖文件")
    
    return True

def create_nodejs_venv(project_name, scripts_dir, repo_dir):
    """创建 Node.js 虚拟环境"""
    # 查找 package.json
    package_files = [
        os.path.join(scripts_dir, "package.json"),
        os.path.join(repo_dir, "package.json"),
    ]
    
    package_json = None
    for pkg_file in package_files:
        if os.path.exists(pkg_file):
            package_json = pkg_file
            break
    
    if not package_json:
        log("⚠️  未找到 package.json")
        return False
    
    log(f"为项目 {project_name} 创建 Node.js 环境...")
    log(f"发现依赖文件: {package_json}")
    
    # 复制 package.json 到 scripts 目录
    if package_json != os.path.join(scripts_dir, "package.json"):
        import shutil
        shutil.copy2(package_json, scripts_dir)
    
    # 安装依赖
    result = subprocess.run([
        "npm", "install", "--production"
    ], cwd=scripts_dir, capture_output=True, text=True)
    
    if result.returncode == 0:
        log("✅ Node.js 依赖安装成功")
        return True
    else:
        log(f"❌ Node.js 依赖安装失败: {result.stderr}")
        return False

def auto_create_venv(subscription_alias):
    """自动为订阅创建虚拟环境"""
    if not subscription_alias:
        log("❌ 未提供订阅别名")
        return False
    
    # 设置路径
    scripts_dir = f"/ql/data/scripts/{subscription_alias}"
    repo_dir = f"/ql/data/repo/{subscription_alias}"
    
    log(f"开始为订阅 {subscription_alias} 自动创建虚拟环境")
    log(f"脚本目录: {scripts_dir}")
    log(f"仓库目录: {repo_dir}")
    
    # 检查目录是否存在
    if not os.path.exists(scripts_dir):
        log(f"⚠️  脚本目录不存在: {scripts_dir}")
        return False
    
    if not os.path.exists(repo_dir):
        log(f"⚠️  仓库目录不存在: {repo_dir}")
        return False
    
    # 检测项目类型
    project_info = detect_project_type(repo_dir)
    
    if not project_info["has_python"] and not project_info["has_nodejs"]:
        log("⚠️  未检测到 Python 或 Node.js 项目，跳过虚拟环境创建")
        return True
    
    success = True
    
    # 创建 Python 虚拟环境
    if project_info["has_python"]:
        log("检测到 Python 项目")
        if not create_python_venv(subscription_alias, scripts_dir, repo_dir):
            success = False
    
    # 创建 Node.js 虚拟环境
    if project_info["has_nodejs"]:
        log("检测到 Node.js 项目")
        if not create_nodejs_venv(subscription_alias, scripts_dir, repo_dir):
            success = False
    
    if success:
        log(f"🎉 订阅 {subscription_alias} 的虚拟环境创建完成")
    else:
        log(f"⚠️  订阅 {subscription_alias} 的虚拟环境创建部分失败")
    
    return success

def main():
    if len(sys.argv) != 2:
        print("用法: python3 auto_create_venv.py <subscription_alias>")
        sys.exit(1)
    
    subscription_alias = sys.argv[1]
    success = auto_create_venv(subscription_alias)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
EOF

    chmod +x "$AUTO_VENV_SCRIPT"
    log_success "虚拟环境自动创建脚本创建完成"
}

# 安装 Shell 脚本补丁
install_shell_patch() {
    log_info "安装 Shell 脚本虚拟环境补丁..."
    
    local UPDATE_SCRIPT="/ql/shell/update.sh"
    
    # 检查是否已经安装
    if grep -q "auto_create_venv_in_shell" "$UPDATE_SCRIPT"; then
        log_warning "Shell 补丁已存在，跳过安装"
        return
    fi
    
    # 备份原文件
    cp "$UPDATE_SCRIPT" "$BACKUP_DIR/update.sh.backup.$(date +%Y%m%d_%H%M%S)"
    
    # 在 update_repo 函数的成功分支中添加虚拟环境创建逻辑
    sed -i.bak '/echo -e "拉取 ${uniq_path} 成功/a\
\
    # 🎯 自动创建虚拟环境 (auto_create_venv_in_shell)\
    if [[ -f "/ql/scripts/qinglong_venv_manager.py" ]]; then\
      echo -e "\\n## 自动创建虚拟环境...\\n"\
      python3 /ql/scripts/qinglong_venv_manager.py create "${uniq_path}" 2>&1 || echo "虚拟环境创建失败，但不影响订阅执行"\
      echo -e "虚拟环境自动创建完成\\n"\
    fi' "$UPDATE_SCRIPT"
    
    # 删除备份文件
    rm -f "$UPDATE_SCRIPT.bak"
    
    log_success "Shell 脚本补丁安装完成"
}

# 复制管理工具
install_manager_tool() {
    log_info "安装虚拟环境管理工具..."
    
    # 检查是否存在管理工具脚本
    local manager_source="./qinglong_venv_manager.py"
    
    if [[ -f "$manager_source" ]]; then
        cp "$manager_source" "$MANAGER_SCRIPT"
        chmod +x "$MANAGER_SCRIPT"
        log_success "虚拟环境管理工具安装完成"
    else
        log_warning "未找到管理工具源文件，将创建基础版本"
        
        # 创建基础管理工具
        cat > "$MANAGER_SCRIPT" << 'EOF'
#!/usr/bin/env python3
"""
青龙虚拟环境管理工具 (基础版)
请使用完整版本获得更多功能
"""
import sys
import os
import subprocess

def main():
    if len(sys.argv) < 2:
        print("用法: python3 qinglong_venv_manager.py <command> [args]")
        print("命令:")
        print("  list    - 列出虚拟环境")
        print("  create  - 创建虚拟环境")
        return
    
    command = sys.argv[1]
    
    if command == "list":
        scripts_dir = "/ql/data/scripts"
        if os.path.exists(scripts_dir):
            for item in os.listdir(scripts_dir):
                venv_path = os.path.join(scripts_dir, item, ".venv")
                if os.path.exists(venv_path):
                    print(f"✅ {item}")
    
    elif command == "create" and len(sys.argv) > 2:
        project_name = sys.argv[2]
        auto_script = "/ql/scripts/auto_create_venv.py"
        if os.path.exists(auto_script):
            subprocess.run([sys.executable, auto_script, project_name])
        else:
            print("❌ 自动创建脚本不存在")

if __name__ == "__main__":
    main()
EOF
        chmod +x "$MANAGER_SCRIPT"
        log_success "基础管理工具创建完成"
    fi
}

# 检查安装状态
check_install_status() {
    log_info "检查安装状态..."
    
    local status_ok=true
    
    # 检查 sitecustomize.py 补丁
    if grep -q "auto_activate_venv_after_env_loaded" "$SITECUSTOMIZE_FILE"; then
        log_success "✅ sitecustomize.py 补丁已安装"
    else
        log_error "❌ sitecustomize.py 补丁未安装"
        status_ok=false
    fi
    
    # 检查 Shell 脚本补丁
    if grep -q "auto_create_venv_in_shell" "/ql/shell/update.sh"; then
        log_success "✅ Shell 脚本补丁已安装"
    else
        log_error "❌ Shell 脚本补丁未安装"
        status_ok=false
    fi
    
    # 检查自动创建脚本
    if [[ -f "$AUTO_VENV_SCRIPT" ]]; then
        log_success "✅ 虚拟环境自动创建脚本已安装"
    else
        log_error "❌ 虚拟环境自动创建脚本未安装"
        status_ok=false
    fi
    
    # 检查管理工具
    if [[ -f "$MANAGER_SCRIPT" ]]; then
        log_success "✅ 虚拟环境管理工具已安装"
    else
        log_error "❌ 虚拟环境管理工具未安装"
        status_ok=false
    fi
    
    # 检查备份
    if [[ -d "$BACKUP_DIR" ]] && [[ -f "$BACKUP_DIR/latest_backup.txt" ]]; then
        local backup_time=$(cat "$BACKUP_DIR/latest_backup.txt")
        log_success "✅ 备份文件存在 (时间: $backup_time)"
    else
        log_warning "⚠️  备份文件不存在"
    fi
    
    echo
    if $status_ok; then
        log_success "🎉 青龙虚拟环境管理系统安装完整"
        echo
        log_info "使用方法:"
        echo "  # 创建虚拟环境"
        echo "  python3 $MANAGER_SCRIPT create <项目名>"
        echo
        echo "  # 列出虚拟环境"
        echo "  python3 $MANAGER_SCRIPT list"
        echo
        echo "  # 重启青龙服务使订阅补丁生效"
        echo "  pm2 restart qinglong"
    else
        log_error "❌ 安装不完整，请运行修复命令"
        echo "  bash $0 repair"
    fi
    
    if $status_ok; then
        return 0
    else
        return 1
    fi
}

# 安装系统
install_system() {
    show_banner
    check_environment
    
    log_info "开始安装青龙虚拟环境管理系统..."
    
    # 创建备份
    create_backup
    
    # 安装各个组件
    install_sitecustomize_patch
    create_auto_venv_script
    install_shell_patch
    install_manager_tool
    
    echo
    log_success "🎉 青龙虚拟环境管理系统安装完成！"
    echo
    log_info "下一步操作:"
    echo "  1. 添加或更新订阅，系统会自动创建虚拟环境"
    echo "  2. 运行 Python 脚本，系统会自动激活虚拟环境"
    echo "  3. 使用管理工具: python3 $MANAGER_SCRIPT list"
    echo
    log_warning "重要提示:"
    echo "  - 请确保项目包含 requirements.txt 或 package.json"
    echo "  - 虚拟环境会在 ql repo 命令执行后自动创建"
    echo "  - Python 脚本会自动使用对应的虚拟环境"
    echo "  - 无需重启青龙服务，Shell 补丁立即生效"
}

# 卸载系统
uninstall_system() {
    log_info "开始卸载青龙虚拟环境管理系统..."
    
    if [[ ! -d "$BACKUP_DIR" ]] || [[ ! -f "$BACKUP_DIR/latest_backup.txt" ]]; then
        log_error "未找到备份文件，无法安全卸载"
        log_error "请手动恢复原始文件或重新安装青龙"
        exit 1
    fi
    
    local backup_time=$(cat "$BACKUP_DIR/latest_backup.txt")
    
    # 恢复 sitecustomize.py
    local sitecustomize_backup="$BACKUP_DIR/sitecustomize.py.backup.$backup_time"
    if [[ -f "$sitecustomize_backup" ]]; then
        cp "$sitecustomize_backup" "$SITECUSTOMIZE_FILE"
        log_success "已恢复 sitecustomize.py"
    else
        log_error "未找到 sitecustomize.py 备份文件"
    fi
    
    # 恢复 Shell 脚本
    local update_backup="$BACKUP_DIR/update.sh.backup.$backup_time"
    if [[ -f "$update_backup" ]]; then
        cp "$update_backup" "/ql/shell/update.sh"
        log_success "已恢复 update.sh"
    else
        log_error "未找到 update.sh 备份文件"
    fi
    
    # 删除安装的脚本
    if [[ -f "$AUTO_VENV_SCRIPT" ]]; then
        rm -f "$AUTO_VENV_SCRIPT"
        log_success "已删除虚拟环境自动创建脚本"
    fi
    
    if [[ -f "$MANAGER_SCRIPT" ]]; then
        rm -f "$MANAGER_SCRIPT"
        log_success "已删除虚拟环境管理工具"
    fi
    
    log_success "🎉 青龙虚拟环境管理系统卸载完成"
    echo
    log_info "请重启青龙服务: pm2 restart qinglong"
    log_info "备份文件保留在: $BACKUP_DIR"
}

# 修复安装
repair_system() {
    log_info "开始修复青龙虚拟环境管理系统..."
    
    # 重新安装所有组件
    install_sitecustomize_patch
    create_auto_venv_script
    install_shell_patch
    install_manager_tool
    
    log_success "🎉 系统修复完成"
    
    # 检查状态
    check_install_status
}

# 显示帮助
show_help() {
    show_banner
    echo -e "${WHITE}🎯 使用方法:${NC}"
    echo "  bash $0                # 🚀 一键安装（推荐）"
    echo "  bash $0 install        # 📦 完整安装"
    echo "  bash $0 uninstall      # 🗑️  卸载系统并恢复原始文件"
    echo "  bash $0 status         # 📊 检查安装状态"
    echo "  bash $0 repair         # 🔧 修复安装"
    echo "  bash $0 help           # ❓ 显示此帮助信息"
    echo
    echo -e "${WHITE}✨ 功能特性:${NC}"
    echo "  ✅ 订阅更新后自动创建虚拟环境"
    echo "  ✅ Python 脚本执行时自动激活虚拟环境"
    echo "  ✅ 支持 Python 和 Node.js 项目"
    echo "  ✅ 完整的备份和恢复机制"
    echo "  ✅ 零配置，开箱即用"
    echo
    echo -e "${WHITE}🎉 安装后使用:${NC}"
    echo "  # 管理虚拟环境"
    echo "  python3 /ql/scripts/qinglong_venv_manager.py list"
    echo "  python3 /ql/scripts/qinglong_venv_manager.py create <项目名>"
    echo
    echo "  # 添加订阅（会自动创建虚拟环境）"
    echo "  ql repo <仓库地址> \"\" \"\" \"requirements.txt\" \"main\" \"py\""
    echo
    echo -e "${YELLOW}💡 提示: 无需重启青龙服务，安装后立即生效！${NC}"
}

# 主函数
main() {
    case "${1:-install}" in
        "install"|"")
            install_system
            ;;
        "uninstall")
            uninstall_system
            ;;
        "status")
            check_install_status
            ;;
        "repair")
            repair_system
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "未知命令: $1"
            echo
            log_info "快速使用："
            echo "  bash $0                # 一键安装（推荐）"
            echo "  bash $0 status         # 查看状态"
            echo "  bash $0 help           # 查看帮助"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
