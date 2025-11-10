# Python 环境管理

本文档说明了如何管理 iDO 项目的 Python 环境、添加新模块、以及处理 Python 依赖。

## 目录

- [环境概览](#环境概览)
- [初始化和同步](#初始化和同步)
- [依赖管理](#依赖管理)
- [项目结构](#项目结构)
- [模块开发](#模块开发)
- [故障排除](#故障排除)

## 环境概览

### 重要的位置信息

iDO 的 Python 环境采用**项目根目录集中管理**的方式：

| 项目 | 位置 | 说明 |
|------|------|------|
| **Python 配置** | `/pyproject.toml` | 项目根目录（**不是** `src-tauri/`） |
| **虚拟环境** | `/.venv/` | 项目根目录 |
| **后端代码** | `/src-tauri/python/` | 实际 Python 代码位置 |
| **后端符号链接** | `/backend/` | 指向 `src-tauri/python/` |

### 为什么这样设计？

```
项目根目录
  ├── pyproject.toml          ← uv 在这里创建 .venv
  ├── .venv/
  ├── src-tauri/
  │   └── python/             ← 实际代码位置
  └── backend/ -> src-tauri/python/  ← 方便访问的符号链接
```

**优势：**
- ✅ Python 虚拟环境在项目根目录，容易管理
- ✅ 所有工具（Tauri、FastAPI 等）共享同一个环境
- ✅ `uv` 自动识别 `pyproject.toml`

## 初始化和同步

### 一键初始化

```bash
# macOS / Linux
pnpm setup

# Windows
pnpm setup:win
```

这会自动执行：
1. ✅ `pnpm install` - 安装 Node.js 依赖
2. ✅ `uv sync` - 创建 `.venv` 并安装 Python 依赖
3. ✅ `pnpm check-i18n` - 验证翻译

### 手动初始化

```bash
# 1. 安装 uv（如果还没安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 进入项目根目录（重要！）
cd /path/to/iDO

# 3. 创建虚拟环境并安装依赖
uv sync

# 4. 验证环境
uv run python --version
```

### 激活虚拟环境

#### macOS / Linux

```bash
# 方法 1：使用 uv
uv run python -c "print('Environment active')"

# 方法 2：手动激活
source .venv/bin/activate

# 验证
python --version
which python  # 应该显示 .venv 路径
```

#### Windows

```bash
# 方法 1：使用 uv（推荐）
uv run python -c "print('Environment active')"

# 方法 2：手动激活
.venv\Scripts\activate

# 验证
python --version
```

## 依赖管理

### 查看当前依赖

```bash
# 列出所有已安装的包
uv pip list

# 显示包的详细信息
uv pip show <package-name>
```

### 添加新依赖

#### 方法 1：编辑 pyproject.toml（推荐）

```toml
# pyproject.toml
[project]
dependencies = [
    "fastapi==0.104.1",
    "pydantic==2.4.2",
    "pynput==1.7.6",
    "mss==9.0.1",
    "pillow==10.0.0",
    "opencv-python==4.8.1.78",
    "openai==1.3.0",
    "python-dotenv==1.0.0",
    "your-new-package==1.0.0",  # 添加新包
]
```

然后同步：

```bash
uv sync
```

#### 方法 2：使用 uv pip install

```bash
# 安装单个包
uv pip install numpy

# 安装多个包
uv pip install numpy pandas scipy

# 安装特定版本
uv pip install numpy==1.24.0

# 更新 pyproject.toml
uv pip compile pyproject.toml -o requirements.txt
```

### 移除依赖

在 `pyproject.toml` 中删除对应的行，然后：

```bash
uv sync
```

### 更新依赖

```bash
# 更新所有依赖到最新版本
uv pip compile --upgrade pyproject.toml

# 仅更新特定包
uv pip install --upgrade numpy
```

### 查看依赖树

```bash
# 显示依赖关系树
uv pip show -d <package-name>
```

### 导出依赖列表

```bash
# 导出到 requirements.txt
uv pip compile pyproject.toml -o requirements.txt

# 查看导出内容
cat requirements.txt
```

## 项目结构

### Python 模块组织

```
src-tauri/python/ido_app/
├── __init__.py              # PyTauri 入口点
├── handlers/
│   ├── __init__.py
│   ├── api_handler.py      # 装饰器定义
│   ├── greeting.py         # 示例处理器
│   ├── perception.py       # 感知层处理器
│   ├── processing.py       # 处理层处理器
│   ├── agents.py           # Agent 处理器
│   └── system.py           # 系统处理器
├── models/
│   ├── __init__.py
│   ├── base.py             # 基础模型和转换
│   ├── requests.py         # 请求模型
│   └── responses.py        # 响应模型
├── db/
│   ├── __init__.py
│   └── database.py         # 数据库操作
├── agents/
│   ├── __init__.py
│   ├── base.py             # Agent 基类
│   ├── factory.py          # Agent 工厂
│   └── ...                 # 具体 Agent 实现
├── perception/
│   ├── __init__.py
│   ├── keyboard.py         # 键盘监控
│   ├── mouse.py            # 鼠标监控
│   └── screenshot.py       # 截图采集
├── processing/
│   ├── __init__.py
│   ├── event_filter.py     # 事件过滤
│   ├── event_aggregator.py # 事件聚合
│   └── llm_summarizer.py   # LLM 总结
└── utils/
    ├── __init__.py
    └── helpers.py          # 工具函数
```

### backend/ 符号链接

```
backend/ -> src-tauri/python/ido_app/
```

这个符号链接允许你这样导入：

```python
# 这两种方式都可以工作
from backend.handlers import api_handler
from src_tauri.python.ido_app.handlers import api_handler
```

## 模块开发

### 创建新模块

#### 步骤 1：创建模块文件

```python
# src-tauri/python/ido_app/handlers/my_module.py
from backend.handlers import api_handler
from backend.models import BaseModel

class MyRequest(BaseModel):
    """我的请求模型"""
    field1: str
    field2: int

@api_handler(body=MyRequest, method="POST", path="/my-endpoint")
async def my_handler(body: MyRequest) -> dict:
    """处理我的请求"""
    return {
        "success": True,
        "data": {
            "field1": body.field1,
            "field2": body.field2
        }
    }
```

#### 步骤 2：导入模块

在 `src-tauri/python/ido_app/__init__.py` 中导入：

```python
# src-tauri/python/ido_app/__init__.py
from . import greeting
from . import perception
from . import processing
from . import agents
from . import system
from . import my_module  # 添加这一行
```

#### 步骤 3：同步环境

```bash
# 重新同步以更新 TypeScript 客户端
pnpm setup-backend

# 或者
uv sync
```

#### 步骤 4：重启应用

```bash
# 重启 Tauri 应用
pnpm tauri dev

# 或启动 FastAPI 服务器测试
uvicorn app:app --reload
```

### 添加新的请求模型

```python
# src-tauri/python/ido_app/models/requests.py
from .base import BaseModel

class MyNewRequest(BaseModel):
    """我的新请求模型"""
    name: str
    value: int = 100  # 有默认值
    optional_field: str | None = None

    class Config:
        # 启用自动 snake_case 到 camelCase 转换
        from_attributes = True
```

### 测试新模块

#### 使用 FastAPI

```bash
# 1. 启动 FastAPI 服务器
uvicorn app:app --reload

# 2. 访问 http://localhost:8000/docs
# 3. 找到你的新端点并测试
```

#### 使用 Python 脚本

```python
# test_my_module.py
import asyncio
from src_tauri.python.ido_app.handlers.my_module import my_handler
from src_tauri.python.ido_app.models.requests import MyRequest

async def test():
    request = MyRequest(field1="test", field2=42)
    result = await my_handler(request)
    print(result)

asyncio.run(test())
```

运行测试：

```bash
uv run python test_my_module.py
```

## 故障排除

### 问题 1：`ModuleNotFoundError`

**错误信息：**
```
ModuleNotFoundError: No module named 'backend'
```

**原因：** 虚拟环境未激活或未正确配置

**解决方案：**

```bash
# 1. 进入项目根目录
cd /path/to/iDO

# 2. 重新同步环境
uv sync

# 3. 验证环境
uv run python -c "import backend; print('OK')"

# 4. 如果还有问题，重新启动
pnpm setup-backend
```

### 问题 2：包版本冲突

**错误信息：**
```
ERROR: pip's dependency resolver does not currently take into account all the packages
that are installed with your environment
```

**解决方案：**

```bash
# 1. 清理虚拟环境
rm -rf .venv

# 2. 重新初始化
uv sync

# 3. 如果还有问题，检查 pyproject.toml 中的版本约束
```

### 问题 3：导入时出现循环依赖

**错误信息：**
```
ImportError: cannot import name 'xxx' from 'backend.handlers'
```

**解决方案：**

```bash
# 1. 检查导入顺序（避免循环导入）
# 2. 使用相对导入而不是绝对导入
#    from ..models import MyModel  # ✅ 相对导入
#    from backend.models import MyModel  # ❌ 可能导致循环导入

# 3. 重启应用
pnpm tauri dev
```

### 问题 4：PyTauri 客户端未更新

**错误信息：**
```
TS2304: Cannot find name 'myHandler'
```

**解决方案：**

```bash
# 1. 确保模块已导入
# src-tauri/python/ido_app/__init__.py 中有 from . import my_module

# 2. 重新同步后端
pnpm setup-backend

# 3. 重启 Tauri
pnpm tauri dev

# 或手动重新生成
pnpm tauri build --ci
```

### 问题 5：Python 版本错误

**错误信息：**
```
The currently activate Python version 3.12.0 does not satisfy the requirement: >=3.14
```

**解决方案：**

```bash
# 1. 检查 Python 版本
python --version

# 2. 更新 Python（使用 homebrew 或官方安装程序）
brew install python@3.14

# 3. 重新创建虚拟环境
rm -rf .venv
uv sync
```

### 问题 6：包安装失败

**错误信息：**
```
ERROR: Failed building wheel for xxx
```

**解决方案：**

```bash
# 1. 更新 pip 和构建工具
uv pip install --upgrade pip setuptools wheel

# 2. 安装必要的开发工具
# macOS
brew install python-dev

# Linux
sudo apt-get install python3-dev build-essential

# Windows（使用 Visual Studio Build Tools）

# 3. 重试安装
uv sync
```

## 最佳实践

### ✅ Python 版本管理

```bash
# 检查指定的 Python 版本
uv python list

# 使用特定版本
uv python install 3.14

# 指定项目使用的 Python 版本
# pyproject.toml
[project]
requires-python = ">=3.14"
```

### ✅ 依赖版本约束

```toml
# pyproject.toml - 推荐的版本约束方式

[project]
dependencies = [
    "fastapi>=0.100,<1.0",      # 允许补丁版本更新
    "pydantic~=2.4",            # 2.4.x 版本
    "pynput==1.7.6",            # 精确版本
    "numpy>=1.20.0",            # 最低版本
]
```

### ✅ 文件组织

```python
# ✅ 好的做法：清晰的模块结构
from backend.handlers.perception import start_keyboard_listener
from backend.models.requests import MyRequest

# ❌ 不好的做法：过长的导入链
from src_tauri.python.ido_app.handlers.perception import start_keyboard_listener
```

### ✅ 异步编程

```python
# ✅ 使用 async/await 处理 I/O 操作
@api_handler(body=MyRequest)
async def my_handler(body: MyRequest) -> dict:
    # 数据库查询
    result = await db.query(...)

    # LLM 调用
    response = await llm_client.create(...)

    return {"result": result}
```

## 获取帮助

- 📖 查看 [后端架构文档](./backend.md)
- 📖 查看 [开发指南](./development.md)
- 📖 查看 [uv 官方文档](https://docs.astral.sh/uv/)
- 🐛 报告 Bug：[GitHub Issues](https://github.com/TexasOct/iDO/issues)
