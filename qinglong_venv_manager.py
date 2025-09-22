#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
青龙虚拟环境管理器
功能：创建、激活、管理虚拟环境的统一工具
版本：1.0.0
作者：QingLong Community
"""

import os
import sys
import subprocess
import json
import argparse
import shutil
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple

class Colors:
    """终端颜色定义"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    NC = '\033[0m'  # No Color

class QingLongVenvManager:
    """青龙虚拟环境管理器"""
    
    def __init__(self):
        self.scripts_dir = "/ql/data/scripts"
        self.repo_dir = "/ql/data/repo"
        self.log_dir = "/ql/data/log"
        
    def log(self, message: str, level: str = "INFO"):
        """带颜色的日志输出"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        color_map = {
            "INFO": Colors.BLUE,
            "SUCCESS": Colors.GREEN,
            "WARNING": Colors.YELLOW,
            "ERROR": Colors.RED,
            "DEBUG": Colors.PURPLE
        }
        
        color = color_map.get(level, Colors.NC)
        print(f"{color}[{timestamp}] [{level}]{Colors.NC} {message}")
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """计算文件的 MD5 哈希值"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            return hashlib.md5(content).hexdigest()
        except Exception as e:
            self.log(f"计算文件哈希失败 {file_path}: {e}", "WARNING")
            return ""
    
    def get_dependency_hashes(self, project_dir: Path, repo_project_dir: Path) -> Dict[str, str]:
        """获取所有依赖文件的哈希值"""
        dependency_files = [
            project_dir / "requirements.txt",
            repo_project_dir / "requirements.txt",
            project_dir / "pyproject.toml",
            repo_project_dir / "pyproject.toml",
            project_dir / "package.json",
            repo_project_dir / "package.json",
            project_dir / "Pipfile",
            repo_project_dir / "Pipfile"
        ]
        
        hashes = {}
        for dep_file in dependency_files:
            if dep_file.exists():
                file_hash = self.calculate_file_hash(dep_file)
                if file_hash:
                    hashes[str(dep_file)] = file_hash
        
        return hashes
    
    def check_dependencies_changed(self, project_name: str) -> bool:
        """检查依赖文件是否发生变化"""
        project_dir = Path(self.scripts_dir) / project_name
        repo_project_dir = Path(self.repo_dir) / project_name
        info_file = project_dir / ".venv_info.json"
        
        # 如果信息文件不存在，认为需要重新安装
        if not info_file.exists():
            return True
        
        try:
            # 读取上次记录的哈希值
            with open(info_file, 'r', encoding='utf-8') as f:
                info_data = json.load(f)
            
            old_hashes = info_data.get("dependency_hashes", {})
            
            # 获取当前的哈希值
            current_hashes = self.get_dependency_hashes(project_dir, repo_project_dir)
            
            # 比较哈希值
            if old_hashes != current_hashes:
                self.log("检测到依赖文件发生变化", "INFO")
                
                # 显示变化的文件
                all_files = set(old_hashes.keys()) | set(current_hashes.keys())
                for file_path in all_files:
                    old_hash = old_hashes.get(file_path, "")
                    new_hash = current_hashes.get(file_path, "")
                    
                    if old_hash != new_hash:
                        if not old_hash:
                            self.log(f"  新增文件: {file_path}", "INFO")
                        elif not new_hash:
                            self.log(f"  删除文件: {file_path}", "INFO")
                        else:
                            self.log(f"  修改文件: {file_path}", "INFO")
                
                return True
            
            return False
            
        except Exception as e:
            self.log(f"检查依赖变化失败: {e}", "WARNING")
            return True  # 出错时重新安装
    
    def detect_project_type(self, project_dir: str) -> Dict[str, any]:
        """检测项目类型和依赖文件"""
        project_path = Path(project_dir)
        
        # Python 项目检测
        python_files = [
            "requirements.txt", "pyproject.toml", 
            "setup.py", "Pipfile", "poetry.lock"
        ]
        
        # Node.js 项目检测
        nodejs_files = [
            "package.json", "yarn.lock", "pnpm-lock.yaml"
        ]
        
        python_deps = [str(project_path / f) for f in python_files if (project_path / f).exists()]
        nodejs_deps = [str(project_path / f) for f in nodejs_files if (project_path / f).exists()]
        
        return {
            "has_python": len(python_deps) > 0,
            "has_nodejs": len(nodejs_deps) > 0,
            "python_deps": python_deps,
            "nodejs_deps": nodejs_deps,
            "project_path": str(project_path)
        }
    
    def create_python_venv(self, project_name: str, force: bool = False) -> bool:
        """创建 Python 虚拟环境"""
        project_dir = Path(self.scripts_dir) / project_name
        repo_project_dir = Path(self.repo_dir) / project_name
        venv_dir = project_dir / ".venv"
        
        self.log(f"为项目 {project_name} 创建 Python 虚拟环境")
        
        # 检查项目目录
        if not project_dir.exists():
            self.log(f"项目目录不存在: {project_dir}", "ERROR")
            return False
        
        # 检查虚拟环境是否已存在
        venv_exists = venv_dir.exists()
        dependencies_changed = self.check_dependencies_changed(project_name)
        
        if venv_exists:
            if not force and not dependencies_changed:
                self.log(f"虚拟环境已存在且依赖未变化: {venv_dir}", "INFO")
                return True
            elif dependencies_changed:
                self.log("依赖文件已更新，重新安装依赖...", "INFO")
                # 不删除虚拟环境，只重新安装依赖
            elif force:
                self.log("强制重建虚拟环境，删除现有环境...", "WARNING")
                shutil.rmtree(venv_dir)
                venv_exists = False
        
        try:
            # 只有在虚拟环境不存在时才创建
            if not venv_exists:
                self.log("创建 Python 虚拟环境...")
                result = subprocess.run([
                    sys.executable, "-m", "venv", str(venv_dir)
                ], capture_output=True, text=True, timeout=300)
                
                if result.returncode != 0:
                    self.log(f"虚拟环境创建失败: {result.stderr}", "ERROR")
                    return False
                
                self.log("✅ Python 虚拟环境创建成功", "SUCCESS")
                
                # 升级 pip
                pip_path = venv_dir / "bin" / "pip"
                self.log("升级 pip...")
                subprocess.run([
                    str(pip_path), "install", "--upgrade", "pip",
                    "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"
                ], capture_output=True, text=True, timeout=120)
            else:
                self.log("✅ Python 虚拟环境已存在", "SUCCESS")
            
            # 安装或更新依赖（无论虚拟环境是否新建都执行）
            self._install_python_dependencies(project_name, venv_dir, project_dir, repo_project_dir, force_reinstall=dependencies_changed or force)
            
            # 创建或更新虚拟环境信息文件
            self._create_venv_info(project_name, venv_dir, project_dir, repo_project_dir)
            
            return True
            
        except subprocess.TimeoutExpired:
            self.log("虚拟环境创建超时", "ERROR")
            return False
        except Exception as e:
            self.log(f"虚拟环境创建异常: {e}", "ERROR")
            return False
    
    def _install_python_dependencies(self, project_name: str, venv_dir: Path, 
                                   project_dir: Path, repo_project_dir: Path, force_reinstall: bool = False):
        """安装 Python 依赖"""
        pip_path = venv_dir / "bin" / "pip"
        
        # 查找依赖文件的优先级顺序
        dependency_files = [
            (project_dir / "requirements.txt", "requirements.txt"),
            (repo_project_dir / "requirements.txt", "requirements.txt"),
            (project_dir / "pyproject.toml", "pyproject.toml"),
            (repo_project_dir / "pyproject.toml", "pyproject.toml"),
            (project_dir / "Pipfile", "Pipfile"),
            (repo_project_dir / "Pipfile", "Pipfile")
        ]
        
        installed = False
        
        for dep_file, dep_type in dependency_files:
            if dep_file.exists():
                self.log(f"发现依赖文件: {dep_file}")
                
                try:
                    if dep_type == "requirements.txt":
                        # 检查文件内容
                        with open(dep_file, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                        
                        if not content or all(line.strip().startswith('#') or not line.strip() 
                                            for line in content.split('\n')):
                            self.log("requirements.txt 文件为空或只包含注释", "WARNING")
                            continue
                        
                        install_cmd = [
                            str(pip_path), "install", "-r", str(dep_file),
                            "-i", "https://pypi.tuna.tsinghua.edu.cn/simple",
                            "--timeout", "300"
                        ]
                        
                        if force_reinstall:
                            install_cmd.append("--force-reinstall")
                            self.log("强制重新安装 requirements.txt 依赖...")
                        else:
                            self.log("安装 requirements.txt 依赖...")
                        
                        result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=600)
                        
                    elif dep_type == "pyproject.toml":
                        self.log("安装 pyproject.toml 项目...")
                        # 复制 pyproject.toml 到项目目录
                        if dep_file != project_dir / "pyproject.toml":
                            shutil.copy2(dep_file, project_dir / "pyproject.toml")
                        
                        result = subprocess.run([
                            str(pip_path), "install", "-e", str(project_dir),
                            "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"
                        ], capture_output=True, text=True, timeout=600)
                        
                    elif dep_type == "Pipfile":
                        self.log("检测到 Pipfile，建议使用 pipenv 管理", "WARNING")
                        continue
                    
                    if result.returncode == 0:
                        self.log("✅ 依赖安装成功", "SUCCESS")
                        installed = True
                        break
                    else:
                        self.log(f"依赖安装失败: {result.stderr}", "WARNING")
                        
                except subprocess.TimeoutExpired:
                    self.log("依赖安装超时", "WARNING")
                except Exception as e:
                    self.log(f"依赖安装异常: {e}", "WARNING")
        
        if not installed:
            self.log("未找到有效的依赖文件或安装失败", "WARNING")
    
    def _create_venv_info(self, project_name: str, venv_dir: Path, project_dir: Path, repo_project_dir: Path = None):
        """创建虚拟环境信息文件"""
        try:
            # 获取 Python 版本
            python_path = venv_dir / "bin" / "python"
            result = subprocess.run([str(python_path), "--version"], 
                                  capture_output=True, text=True)
            python_version = result.stdout.strip() if result.returncode == 0 else "未知版本"
            
            # 获取已安装包数量
            pip_path = venv_dir / "bin" / "pip"
            result = subprocess.run([str(pip_path), "list", "--format=freeze"], 
                                  capture_output=True, text=True)
            packages = [line for line in result.stdout.split('\n') if line.strip()]
            
            # 获取依赖文件哈希值
            if repo_project_dir is None:
                repo_project_dir = Path(self.repo_dir) / project_name
            dependency_hashes = self.get_dependency_hashes(project_dir, repo_project_dir)
            
            # 读取现有信息文件以保留创建时间
            info_file = project_dir / ".venv_info.json"
            created_at = datetime.now().isoformat()
            if info_file.exists():
                try:
                    with open(info_file, 'r', encoding='utf-8') as f:
                        existing_info = json.load(f)
                    created_at = existing_info.get("created_at", created_at)
                except:
                    pass
            
            venv_info = {
                "project_name": project_name,
                "project_dir": str(project_dir),
                "venv_dir": str(venv_dir),
                "python_path": str(python_path),
                "pip_path": str(pip_path),
                "site_packages": str(venv_dir / "lib" / "python3.11" / "site-packages"),
                "python_version": python_version,
                "package_count": len(packages),
                "dependency_hashes": dependency_hashes,
                "last_updated": datetime.now().isoformat(),
                "created_at": created_at,
                "manager": "qinglong_venv_manager"
            }
            
            info_file = project_dir / ".venv_info.json"
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(venv_info, f, indent=2, ensure_ascii=False)
            
            self.log(f"虚拟环境信息已保存: {info_file}")
            
        except Exception as e:
            self.log(f"创建虚拟环境信息文件失败: {e}", "WARNING")
    
    def create_nodejs_env(self, project_name: str, force: bool = False) -> bool:
        """创建 Node.js 环境"""
        project_dir = Path(self.scripts_dir) / project_name
        repo_project_dir = Path(self.repo_dir) / project_name
        node_modules_dir = project_dir / "node_modules"
        
        self.log(f"为项目 {project_name} 创建 Node.js 环境")
        
        # 检查项目目录
        if not project_dir.exists():
            self.log(f"项目目录不存在: {project_dir}", "ERROR")
            return False
        
        # 检查 Node.js 环境是否已存在
        nodejs_exists = node_modules_dir.exists()
        dependencies_changed = self.check_dependencies_changed(project_name)
        
        if nodejs_exists:
            if not force and not dependencies_changed:
                self.log(f"Node.js 环境已存在且依赖未变化: {node_modules_dir}", "INFO")
                return True
            elif dependencies_changed:
                self.log("package.json 已更新，重新安装依赖...", "INFO")
                # 删除 node_modules 以确保完全重新安装
                shutil.rmtree(node_modules_dir)
                nodejs_exists = False
            elif force:
                self.log("强制重建 Node.js 环境，删除现有环境...", "WARNING")
                shutil.rmtree(node_modules_dir)
                nodejs_exists = False
        
        # 查找 package.json
        package_files = [
            project_dir / "package.json",
            repo_project_dir / "package.json"
        ]
        
        package_json = None
        for pkg_file in package_files:
            if pkg_file.exists():
                package_json = pkg_file
                break
        
        if not package_json:
            self.log("未找到 package.json 文件", "ERROR")
            return False
        
        try:
            self.log(f"发现依赖文件: {package_json}")
            
            # 复制 package.json 到项目目录
            target_package = project_dir / "package.json"
            if package_json != target_package:
                shutil.copy2(package_json, target_package)
                self.log(f"已复制 package.json 到: {target_package}")
            
            # 安装依赖
            self.log("安装 Node.js 依赖...")
            result = subprocess.run([
                "npm", "install", "--production", "--no-audit"
            ], cwd=str(project_dir), capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                self.log("✅ Node.js 依赖安装成功", "SUCCESS")
                return True
            else:
                self.log(f"Node.js 依赖安装失败: {result.stderr}", "ERROR")
                return False
                
        except subprocess.TimeoutExpired:
            self.log("Node.js 依赖安装超时", "ERROR")
            return False
        except Exception as e:
            self.log(f"Node.js 环境创建异常: {e}", "ERROR")
            return False
    
    def create_venv(self, project_name: str, force: bool = False) -> bool:
        """自动检测并创建虚拟环境"""
        self.log("=" * 60)
        self.log(f"开始为项目 {project_name} 创建虚拟环境")
        self.log("=" * 60)
        
        # 检查项目目录
        project_dir = Path(self.scripts_dir) / project_name
        repo_project_dir = Path(self.repo_dir) / project_name
        
        if not project_dir.exists():
            self.log(f"脚本目录不存在: {project_dir}", "ERROR")
            return False
        
        # 检测项目类型
        project_info = self.detect_project_type(str(repo_project_dir))
        
        if not project_info["has_python"] and not project_info["has_nodejs"]:
            self.log("未检测到 Python 或 Node.js 项目配置文件", "WARNING")
            self.log("支持的配置文件:")
            self.log("  Python: requirements.txt, pyproject.toml, setup.py, Pipfile")
            self.log("  Node.js: package.json, yarn.lock, pnpm-lock.yaml")
            return False
        
        success = True
        
        # 创建 Python 虚拟环境
        if project_info["has_python"]:
            self.log("检测到 Python 项目", "INFO")
            for dep_file in project_info["python_deps"]:
                self.log(f"  - {dep_file}")
            
            if not self.create_python_venv(project_name, force):
                success = False
        
        # 创建 Node.js 环境
        if project_info["has_nodejs"]:
            self.log("检测到 Node.js 项目", "INFO")
            for dep_file in project_info["nodejs_deps"]:
                self.log(f"  - {dep_file}")
            
            if not self.create_nodejs_env(project_name, force):
                success = False
        
        if success:
            self.log("=" * 60)
            self.log(f"🎉 项目 {project_name} 虚拟环境创建完成", "SUCCESS")
            self.log("=" * 60)
        else:
            self.log("=" * 60)
            self.log(f"⚠️  项目 {project_name} 虚拟环境创建部分失败", "WARNING")
            self.log("=" * 60)
        
        return success
    
    def remove_venv(self, project_name: str) -> bool:
        """删除虚拟环境"""
        project_dir = Path(self.scripts_dir) / project_name
        venv_dir = project_dir / ".venv"
        node_modules_dir = project_dir / "node_modules"
        info_file = project_dir / ".venv_info.json"
        
        self.log(f"删除项目 {project_name} 的虚拟环境")
        
        removed = False
        
        # 删除 Python 虚拟环境
        if venv_dir.exists():
            try:
                shutil.rmtree(venv_dir)
                self.log(f"✅ 已删除 Python 虚拟环境: {venv_dir}", "SUCCESS")
                removed = True
            except Exception as e:
                self.log(f"删除 Python 虚拟环境失败: {e}", "ERROR")
        
        # 删除 Node.js 环境
        if node_modules_dir.exists():
            try:
                shutil.rmtree(node_modules_dir)
                self.log(f"✅ 已删除 Node.js 环境: {node_modules_dir}", "SUCCESS")
                removed = True
            except Exception as e:
                self.log(f"删除 Node.js 环境失败: {e}", "ERROR")
        
        # 删除信息文件
        if info_file.exists():
            try:
                info_file.unlink()
                self.log(f"✅ 已删除信息文件: {info_file}", "SUCCESS")
            except Exception as e:
                self.log(f"删除信息文件失败: {e}", "WARNING")
        
        if not removed:
            self.log(f"项目 {project_name} 没有虚拟环境需要删除", "WARNING")
            return False
        
        return True
    
    def list_venvs(self) -> List[Dict[str, any]]:
        """列出所有虚拟环境"""
        self.log("扫描虚拟环境...")
        
        if not Path(self.scripts_dir).exists():
            self.log(f"脚本目录不存在: {self.scripts_dir}", "ERROR")
            return []
        
        venvs = []
        
        for item in Path(self.scripts_dir).iterdir():
            if item.is_dir():
                project_name = item.name
                venv_dir = item / ".venv"
                node_modules_dir = item / "node_modules"
                info_file = item / ".venv_info.json"
                
                venv_info = {
                    "project_name": project_name,
                    "project_dir": str(item),
                    "has_python_venv": venv_dir.exists(),
                    "has_nodejs_env": node_modules_dir.exists(),
                    "python_version": "未知",
                    "package_count": 0,
                    "created_at": "未知",
                    "status": "未知"
                }
                
                # 读取详细信息
                if info_file.exists():
                    try:
                        with open(info_file, 'r', encoding='utf-8') as f:
                            info_data = json.load(f)
                        venv_info.update({
                            "python_version": info_data.get("python_version", "未知"),
                            "package_count": info_data.get("package_count", 0),
                            "created_at": info_data.get("created_at", "未知")
                        })
                    except Exception as e:
                        self.log(f"读取 {info_file} 失败: {e}", "DEBUG")
                
                # 检查虚拟环境状态
                if venv_dir.exists():
                    python_path = venv_dir / "bin" / "python"
                    if python_path.exists():
                        try:
                            result = subprocess.run([str(python_path), "--version"], 
                                                  capture_output=True, text=True, timeout=5)
                            if result.returncode == 0:
                                venv_info["status"] = "正常"
                                if venv_info["python_version"] == "未知":
                                    venv_info["python_version"] = result.stdout.strip()
                            else:
                                venv_info["status"] = "异常"
                        except:
                            venv_info["status"] = "异常"
                    else:
                        venv_info["status"] = "损坏"
                elif node_modules_dir.exists():
                    venv_info["status"] = "Node.js"
                
                if venv_info["has_python_venv"] or venv_info["has_nodejs_env"]:
                    venvs.append(venv_info)
        
        return venvs
    
    def show_venv_list(self):
        """显示虚拟环境列表"""
        venvs = self.list_venvs()
        
        if not venvs:
            self.log("未找到任何虚拟环境", "WARNING")
            self.log("")
            self.log("创建虚拟环境:")
            self.log("  python3 qinglong_venv_manager.py create <项目名>")
            return
        
        self.log("虚拟环境列表:")
        self.log("=" * 100)
        
        # 表头
        print(f"{Colors.WHITE}{'项目名':<25} {'类型':<15} {'Python版本':<20} {'包数量':<10} {'状态':<10} {'创建时间':<20}{Colors.NC}")
        print("-" * 100)
        
        # 数据行
        for venv in sorted(venvs, key=lambda x: x["project_name"]):
            project_name = venv["project_name"][:24]
            
            # 确定类型
            types = []
            if venv["has_python_venv"]:
                types.append("Python")
            if venv["has_nodejs_env"]:
                types.append("Node.js")
            venv_type = "+".join(types)
            
            python_version = venv["python_version"].replace("Python ", "") if venv["python_version"] != "未知" else "-"
            package_count = str(venv["package_count"]) if venv["package_count"] > 0 else "-"
            status = venv["status"]
            
            # 创建时间格式化
            created_at = venv["created_at"]
            if created_at != "未知":
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    created_at = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    created_at = created_at[:16]
            
            # 状态颜色
            status_color = Colors.GREEN if status == "正常" else Colors.YELLOW if status == "Node.js" else Colors.RED
            
            print(f"{project_name:<25} {venv_type:<15} {python_version:<20} {package_count:<10} "
                  f"{status_color}{status:<10}{Colors.NC} {created_at:<20}")
        
        print("-" * 100)
        self.log(f"共找到 {len(venvs)} 个虚拟环境", "INFO")
    
    def show_venv_info(self, project_name: str):
        """显示特定项目的虚拟环境信息"""
        project_dir = Path(self.scripts_dir) / project_name
        
        if not project_dir.exists():
            self.log(f"项目不存在: {project_name}", "ERROR")
            return
        
        self.log(f"项目 {project_name} 虚拟环境信息:")
        self.log("=" * 60)
        
        venv_dir = project_dir / ".venv"
        node_modules_dir = project_dir / "node_modules"
        info_file = project_dir / ".venv_info.json"
        
        # 基本信息
        print(f"项目名称: {Colors.CYAN}{project_name}{Colors.NC}")
        print(f"项目目录: {project_dir}")
        
        # Python 虚拟环境信息
        if venv_dir.exists():
            print(f"\n{Colors.GREEN}✅ Python 虚拟环境{Colors.NC}")
            print(f"  虚拟环境目录: {venv_dir}")
            
            python_path = venv_dir / "bin" / "python"
            if python_path.exists():
                try:
                    # Python 版本
                    result = subprocess.run([str(python_path), "--version"], 
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        print(f"  Python 版本: {result.stdout.strip()}")
                    
                    # 已安装包
                    pip_path = venv_dir / "bin" / "pip"
                    result = subprocess.run([str(pip_path), "list", "--format=freeze"], 
                                          capture_output=True, text=True)
                    if result.returncode == 0:
                        packages = [line for line in result.stdout.split('\n') if line.strip()]
                        print(f"  已安装包数量: {len(packages)}")
                        
                        if packages:
                            print("  主要依赖包:")
                            for pkg in packages[:10]:  # 显示前10个
                                if '==' in pkg:
                                    name, version = pkg.split('==', 1)
                                    print(f"    - {name} ({version})")
                            if len(packages) > 10:
                                print(f"    ... 还有 {len(packages) - 10} 个包")
                
                except Exception as e:
                    print(f"  状态: {Colors.RED}异常 - {e}{Colors.NC}")
            else:
                print(f"  状态: {Colors.RED}损坏 - Python 可执行文件不存在{Colors.NC}")
        else:
            print(f"\n{Colors.YELLOW}❌ Python 虚拟环境未创建{Colors.NC}")
        
        # Node.js 环境信息
        if node_modules_dir.exists():
            print(f"\n{Colors.GREEN}✅ Node.js 环境{Colors.NC}")
            print(f"  node_modules 目录: {node_modules_dir}")
            
            package_json = project_dir / "package.json"
            if package_json.exists():
                try:
                    with open(package_json, 'r', encoding='utf-8') as f:
                        pkg_data = json.load(f)
                    
                    print(f"  项目名称: {pkg_data.get('name', '未知')}")
                    print(f"  项目版本: {pkg_data.get('version', '未知')}")
                    
                    deps = pkg_data.get('dependencies', {})
                    dev_deps = pkg_data.get('devDependencies', {})
                    print(f"  生产依赖: {len(deps)} 个")
                    print(f"  开发依赖: {len(dev_deps)} 个")
                    
                except Exception as e:
                    print(f"  package.json 读取失败: {e}")
        else:
            print(f"\n{Colors.YELLOW}❌ Node.js 环境未创建{Colors.NC}")
        
        # 详细信息文件
        if info_file.exists():
            try:
                with open(info_file, 'r', encoding='utf-8') as f:
                    info_data = json.load(f)
                
                print(f"\n{Colors.BLUE}📋 详细信息{Colors.NC}")
                print(f"  创建时间: {info_data.get('created_at', '未知')}")
                print(f"  管理器: {info_data.get('manager', '未知')}")
                
            except Exception as e:
                print(f"\n详细信息读取失败: {e}")
        
        print("=" * 60)
    
    def activate_venv_command(self, project_name: str):
        """生成虚拟环境激活命令"""
        project_dir = Path(self.scripts_dir) / project_name
        venv_dir = project_dir / ".venv"
        
        if not project_dir.exists():
            self.log(f"项目不存在: {project_name}", "ERROR")
            return
        
        if not venv_dir.exists():
            self.log(f"项目 {project_name} 没有 Python 虚拟环境", "ERROR")
            self.log("请先创建虚拟环境:")
            self.log(f"  python3 qinglong_venv_manager.py create {project_name}")
            return
        
        activate_script = venv_dir / "bin" / "activate"
        if not activate_script.exists():
            self.log(f"激活脚本不存在: {activate_script}", "ERROR")
            return
        
        self.log(f"项目 {project_name} 虚拟环境激活命令:")
        self.log("=" * 60)
        print(f"{Colors.GREEN}# 激活虚拟环境{Colors.NC}")
        print(f"cd {project_dir}")
        print(f"source {activate_script}")
        print()
        print(f"{Colors.GREEN}# 或者直接使用虚拟环境的 Python{Colors.NC}")
        print(f"{venv_dir}/bin/python your_script.py")
        print()
        print(f"{Colors.GREEN}# 退出虚拟环境{Colors.NC}")
        print("deactivate")
        self.log("=" * 60)

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="青龙虚拟环境管理器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 创建虚拟环境
  python3 qinglong_venv_manager.py create my_project
  
  # 强制重建虚拟环境
  python3 qinglong_venv_manager.py create my_project --force
  
  # 列出所有虚拟环境
  python3 qinglong_venv_manager.py list
  
  # 查看项目详细信息
  python3 qinglong_venv_manager.py info my_project
  
  # 删除虚拟环境
  python3 qinglong_venv_manager.py remove my_project
  
  # 获取激活命令
  python3 qinglong_venv_manager.py activate my_project
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # create 命令
    create_parser = subparsers.add_parser('create', help='创建虚拟环境')
    create_parser.add_argument('project', help='项目名称')
    create_parser.add_argument('--force', action='store_true', help='强制重建虚拟环境')
    
    # list 命令
    subparsers.add_parser('list', help='列出所有虚拟环境')
    
    # info 命令
    info_parser = subparsers.add_parser('info', help='显示项目虚拟环境详细信息')
    info_parser.add_argument('project', help='项目名称')
    
    # remove 命令
    remove_parser = subparsers.add_parser('remove', help='删除虚拟环境')
    remove_parser.add_argument('project', help='项目名称')
    
    # activate 命令
    activate_parser = subparsers.add_parser('activate', help='显示虚拟环境激活命令')
    activate_parser.add_argument('project', help='项目名称')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = QingLongVenvManager()
    
    try:
        if args.command == 'create':
            success = manager.create_venv(args.project, args.force)
            sys.exit(0 if success else 1)
            
        elif args.command == 'list':
            manager.show_venv_list()
            
        elif args.command == 'info':
            manager.show_venv_info(args.project)
            
        elif args.command == 'remove':
            success = manager.remove_venv(args.project)
            sys.exit(0 if success else 1)
            
        elif args.command == 'activate':
            manager.activate_venv_command(args.project)
            
    except KeyboardInterrupt:
        manager.log("操作被用户中断", "WARNING")
        sys.exit(1)
    except Exception as e:
        manager.log(f"执行失败: {e}", "ERROR")
        sys.exit(1)

if __name__ == "__main__":
    main()
