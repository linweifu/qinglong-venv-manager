# 🚀 青龙虚拟环境管理器

为青龙面板提供完全自动化的虚拟环境管理解决方案。

## ✨ 特性

- 🎯 **零配置** - 安装后即可使用，无需任何配置
- 🔄 **自动创建** - 订阅更新时自动创建虚拟环境
- ⚡ **自动激活** - Python 脚本执行时自动激活虚拟环境
- 🛡️ **完全隔离** - 每个项目独立的依赖环境
- 🎨 **美观界面** - 彩色终端输出和详细状态信息

## 🚀 快速开始

### 一键安装

```bash
# 下载安装器
wget -O qinglong_venv_installer.sh https://raw.githubusercontent.com/.../qinglong_venv_installer.sh

# 🎯 一键安装（推荐）
bash qinglong_venv_installer.sh

# 或者显式安装
bash qinglong_venv_installer.sh install

# 验证安装
bash qinglong_venv_installer.sh status
```

### 使用方法

```bash
# 列出所有虚拟环境
python3 /ql/scripts/qinglong_venv_manager.py list

# 创建虚拟环境
python3 /ql/scripts/qinglong_venv_manager.py create <项目名>

# 查看项目详情
python3 /ql/scripts/qinglong_venv_manager.py info <项目名>

# 删除虚拟环境
python3 /ql/scripts/qinglong_venv_manager.py remove <项目名>
```

## 📋 核心文件

| 文件 | 功能 | 说明 |
|------|------|------|
| `qinglong_venv_installer.sh` | 🚀 一键安装器 | 唯一安装入口，包含所有功能 |
| `qinglong_venv_manager.py` | 🔧 虚拟环境管理器 | 创建、管理虚拟环境 |
| `env-to-json.py` | 🔄 环境变量转换工具 | 将 .env 文件转换为 JSON |
| `COMPLETE_SOLUTION_GUIDE.md` | 📖 完整技术文档 | 详细的实施指南和技术原理 |

## 🎯 工作原理

1. **Shell 脚本补丁** - 修改 `/ql/shell/update.sh`，在订阅更新后自动创建虚拟环境
2. **sitecustomize.py 补丁** - 修改 Python 启动脚本，自动激活虚拟环境
3. **智能检测** - 自动识别 Python/Node.js 项目并安装对应依赖

## 📖 详细文档

查看 [完整解决方案指南](COMPLETE_SOLUTION_GUIDE.md) 了解：
- 详细的技术原理
- 完整的实施步骤
- 故障排除指南
- 最佳实践建议

## 🛠️ 系统要求

- 青龙面板 (任意版本)
- Python 3.8+
- Node.js 14+ (可选，用于 Node.js 项目)
- root 或 sudo 权限

## 🎉 使用效果

安装后，您的青龙面板将拥有：

```bash
# 🎯 一键安装
bash qinglong_venv_installer.sh

# 输出：
🚀 青龙虚拟环境管理器
✨ 零配置、自动创建、自动激活、完全隔离
🎯 让虚拟环境管理变得简单、自动、可靠！

🎉 青龙虚拟环境管理系统安装完成！
```

```bash
# 执行订阅时自动创建虚拟环境
ql repo "https://github.com/user/project.git" "" "" "requirements.txt" "main" "py"

# 输出：
拉取 project_main 成功...

## 自动创建虚拟环境...

[INFO] 为项目 project_main 创建虚拟环境
[SUCCESS] ✅ Python 虚拟环境创建成功
[SUCCESS] ✅ 依赖安装成功

虚拟环境自动创建完成
```

```bash
# 执行 Python 脚本时自动激活虚拟环境
# 日志输出：
[VENV_AUTO] ✅ 已激活虚拟环境: project_main
[VENV_AUTO] 虚拟环境路径: /ql/data/scripts/project_main/.venv/lib/python3.11/site-packages
```

## 🤝 贡献

欢迎贡献代码、报告问题或提出建议！

## 📄 许可证

MIT License

---

**🎉 让虚拟环境管理变得简单、自动、可靠！**
