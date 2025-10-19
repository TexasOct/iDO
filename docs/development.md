# 开发环境配置指南

本文档介绍如何配置 Rewind 项目的开发环境，包括前端和 Python 后端的设置。

## 快速开始

如果你只是想快速开始开发，运行以下命令之一即可：

**macOS / Linux:**

```bash
pnpm setup
```

**Windows:**

```bash
pnpm setup:win
```

或者手动运行完整初始化：

```bash
pnpm setup-all
```

这将自动完成所有环境初始化步骤。

## 项目结构概览

```
rewind/
├── src/                    # 前端 React 代码
├── src-tauri/             # Tauri 应用配置
│   ├── python/            # Python 后端代码（PyTauri）
│   ├── src/               # Rust 代码
│   └── Cargo.toml         # Rust 依赖
├── package.json           # Node.js 依赖
├── pyproject.toml         # Python 项目配置（项目根目录）
├── pnpm-lock.yaml         # pnpm 锁定文件
└── docs/                  # 文档
```

## 前置要求

- **Node.js**: v18 或以上
- **Rust**: 最新稳定版（[安装 Rust](https://rustup.rs/)）
- **Python**: 3.13 或以上
- **uv**: Python 包管理工具（[安装 uv](https://docs.astral.sh/uv/getting-started/installation/)）
- **pnpm**: Node.js 包管理工具（`npm install -g pnpm`）

## 前端环境配置

### 1. 安装 Node.js 依赖

```bash
# 进入项目根目录
cd rewind

# 使用 pnpm 安装依赖
pnpm install
```

### 2. 前端开发命令

```bash
# 启动前端开发服务器（仅前端，不含 Tauri）
pnpm dev

# 构建前端
pnpm build

# 代码格式检查
pnpm lint

# 代码格式化
pnpm format

# 检查 i18n 翻译键一致性
pnpm check-i18n
```

### 3. Tauri 相关命令

```bash
# 启动 Tauri 应用（包含前端 + 后端）
pnpm tauri dev

# 构建发布版本
pnpm tauri build
```

## Python 后端环境配置

### 1. 使用 uv 初始化后端环境

```bash
# 在项目根目录运行（无需进入 src-tauri）
uv sync
```

这将自动在项目根目录下创建 `.venv` 目录并安装所有 Python 依赖。

> **提示**: `uv sync` 是一个一体化命令，无需手动创建虚拟环境或激活它。uv 会自动处理所有环境管理。

### 2. 验证后端环境

要验证 Python 环境是否正确设置，可以查看虚拟环境的存在：

```bash
ls .venv
```

或者检查 Python 版本：

```bash
./.venv/bin/python --version
```

### 3. Python 依赖说明

项目的 Python 依赖定义在项目根目录的 `pyproject.toml`：

```toml
[project]
name = "tauri-app"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "pytauri == 0.8.*",    # Python-Rust 桥梁
    "pydantic == 2.*",     # 数据验证
    "anyio == 4.*",        # 异步 I/O
    # ... 其他依赖
]
```

### 5. PyTauri 集成

PyTauri 是一个 Python-Rust 通信框架。项目中的 Python 代码通过 PyTauri 与 Tauri（Rust）进行交互。

**PyTauri 入口配置** (`pyproject.toml`)：

```toml
[project.entry-points.pytauri]
ext_mod = "tauri_app.ext_mod"
```

这告诉 PyTauri 在启动时加载 `tauri_app.ext_mod` 模块。

**Python 代码位置**：

- `src-tauri/python/` - Python 源代码根目录
- `src-tauri/python/tauri_app/` - 主应用模块

### 6. 自动生成 TypeScript 客户端

当修改 Python 后端的公共接口时，需要重新生成 TypeScript 客户端绑定：

```bash
# 从项目根目录运行
pnpm tauri dev  # 会自动重新生成

# 或手动生成
cd src-tauri
cargo build
```

这会自动生成 `src/client/` 目录下的 TypeScript 代码，供前端调用。

### 7. 添加新的 Python 模块

当需要添加新的 Python 功能时，按照以下步骤创建新模块：

#### 7.1 创建模块结构

在 `src-tauri/python/` 下创建新的模块文件夹和文件：

```bash
# 进入 Python 目录
cd src-tauri/python

# 创建新的功能模块，例如数据处理模块
mkdir -p myfeature
touch myfeature/__init__.py
touch myfeature/processor.py
```

或者直接创建单个模块文件：

```bash
# 创建单个模块文件
touch myfeature.py
```

#### 7.2 编写模块代码

例如 `src-tauri/python/myfeature/processor.py`：

```python
from pydantic import BaseModel

class ProcessResult(BaseModel):
    """处理结果数据模型"""
    status: str
    message: str
    data: dict

async def process_data(input_data: dict) -> ProcessResult:
    """处理数据的异步函数"""
    # 实现具体逻辑
    return ProcessResult(
        status="success",
        message="处理完成",
        data={"processed": input_data}
    )
```

#### 7.3 在入口模块中暴露接口

编辑 `src-tauri/python/tauri_app/__init__.py`，导入并暴露新模块：

```python
from myfeature.processor import process_data

__all__ = [
    "process_data",
    # 其他已有的导出
]
```

或者如果使用单个文件：

```python
from myfeature import some_function

__all__ = [
    "some_function",
]
```

#### 7.4 更新项目

修改完 Python 代码后，需要重新同步包以使新模块生效。在项目根目录运行：

```bash
# 直接在项目根目录运行
uv sync
```

或者使用 pnpm 快捷命令（推荐）：

```bash
pnpm setup-backend
```

**重要**: 这个步骤是必需的，只有运行后新的 Python 模块才能被 PyTauri 识别。

#### 7.5 重新生成 TypeScript 客户端

新的 Python 函数需要重新生成 TypeScript 绑定：

```bash
# 从项目根目录运行
pnpm tauri dev

# 或手动重建
cd src-tauri
cargo build
```

重新生成后，TypeScript 客户端代码会更新在 `src/client/apiClient.ts` 中。

#### 7.6 在前端使用新模块

生成后，可以在前端代码中导入并使用：

```typescript
// src/lib/services/myfeature.ts
import { apiClient } from '@/client/apiClient'

export async function processData(inputData: Record<string, any>) {
  return await apiClient.processData(inputData)
}
```

然后在组件中使用：

```tsx
import { processData } from '@/lib/services/myfeature'

export function MyComponent() {
  const handleProcess = async () => {
    const result = await processData({ key: 'value' })
    console.log(result)
  }

  return <button onClick={handleProcess}>Process</button>
}
```

#### 7.7 添加模块依赖

如果新模块需要额外的 Python 包，编辑项目根目录的 `pyproject.toml`：

```toml
[project]
dependencies = [
    "pytauri == 0.8.*",
    "pydantic == 2.*",
    "anyio == 4.*",
    # 添加新依赖
    "requests == 2.*",
    "numpy == 1.*",
]
```

然后在项目根目录重新安装（推荐）：

```bash
pnpm setup-backend
```

或者手动运行：

```bash
uv sync
```

## 完整的开发工作流

### 初始化环境

第一次开发前，运行以下命令进行完整的环境初始化：

```bash
# macOS / Linux
pnpm setup

# 或 Windows
pnpm setup:win

# 或手动运行
pnpm setup-all
```

### 场景 1: 只修改前端代码

```bash
# 仅启动前端开发服务器
pnpm dev

# 在浏览器中访问 http://localhost:5173
```

### 场景 2: 修改前端和后端代码

```bash
# 启动完整的 Tauri 应用（包含前端热重载）
pnpm tauri dev

# 此时前端改动会自动热重载
# 后端改动需要重新启动应用
```

### 场景 3: 修改 Python 代码

#### 如果只修改了现有代码逻辑

```bash
# 1. 在 src-tauri/python 中修改 Python 代码
# 2. 重新启动 Tauri 应用
pnpm tauri dev
```

#### 如果添加了新的 Python 模块或修改了 pyproject.toml

```bash
# 1. 创建新的 Python 模块（参考 7. 添加新的 Python 模块）
# 2. 同步后端环境（重要步骤！）在项目根目录运行：
pnpm setup-backend

# 或手动运行
uv sync

# 3. 重新生成 TypeScript 客户端
pnpm tauri dev
```

**注意**: 添加新模块或添加新依赖后必须运行 `uv sync` 或 `pnpm setup-backend`，否则 PyTauri 无法识别新模块。

## 环境变量配置

项目支持以下环境变量（可选）：

```bash
# 指定 Python 可执行文件位置（一般不需要）
export PYTHON_EXECUTABLE=/usr/bin/python3

# 启用详细日志
export RUST_LOG=debug
```

## 常见问题

### Q: 如何快速初始化整个项目？

A: 使用一条命令初始化所有环境：

```bash
# macOS / Linux
pnpm setup

# Windows
pnpm setup:win

# 或手动运行所有步骤
pnpm setup-all
```

### Q: 如何重置虚拟环境？

A: 删除并重新同步（在项目根目录运行）：

```bash
# 删除旧环境
rm -rf .venv

# 重新同步（在项目根目录）
uv sync

# 或使用 pnpm
pnpm setup-backend
```

### Q: 启动 `pnpm tauri dev` 时出现 Python 错误？

A: 确保：

1. 虚拟环境已正确初始化：运行 `pnpm setup-backend` 或 `uv sync`（在项目根目录）
2. Python 依赖已正确安装：检查 `.venv` 目录存在
3. 检查 `RUST_LOG=debug pnpm tauri dev` 查看详细错误信息

### Q: 前端和后端如何通信？

A: 通过自动生成的 PyTauri 客户端：

```typescript
// src/lib/services/example.ts
import { apiClient } from '@/client/apiClient'

export async function exampleFunction() {
  return await apiClient.pythonMethodName(params)
}
```

对应的 Python 后端需要在 PyTauri 中公开该方法。

### Q: 如何调试 Python 代码？

A: 在 Python 代码中添加调试信息：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def my_function():
    logger.debug("Debug information")
    logger.info("Info message")
    logger.error("Error message")
```

然后运行：

```bash
RUST_LOG=debug pnpm tauri dev
```

### Q: 添加了新的 Python 模块后，前端看不到怎么办？

A: 确保你完成了以下步骤：

1. 在 `src-tauri/python/` 创建了新的模块文件和 `__init__.py`
2. 在 `src-tauri/python/tauri_app/__init__.py` 中导入并暴露了新函数
3. **运行了** `pnpm setup-backend` 或 `uv sync` 来更新项目（在项目根目录，这是最常被遗漏的步骤！）
4. 重新运行 `pnpm tauri dev` 来重新生成 TypeScript 客户端

如果还是看不到，尝试：

```bash
# 完整的重建流程（在项目根目录运行）
uv sync                    # 重新同步环境
cargo clean                # 清理 Rust 缓存
pnpm tauri dev             # 重新启动应用
```

### Q: 如何在不启动 Tauri 的情况下测试 Python 代码？

A: uv 会自动在虚拟环境中运行命令，无需手动激活。直接创建测试脚本 `test_my_module.py`（在项目根目录）：

```python
import asyncio
from tauri_app.myfeature.processor import process_data

async def main():
    result = await process_data({'test': 'data'})
    print(result)

if __name__ == '__main__':
    asyncio.run(main())
```

然后使用 uv 运行（在项目根目录）：

```bash
uv run python test_my_module.py
```

或者直接导入运行：

```bash
uv run python -c "from tauri_app.myfeature.processor import process_data; import asyncio; print(asyncio.run(process_data({'test': 'data'})))"
```

## 最佳实践

1. **初次开发使用 `pnpm setup`**：一条命令完成所有环境初始化
2. **定期同步依赖**：当 `package.json` 或 `pyproject.toml` 变更时，重新运行 `pnpm setup-all` 或对应的 `setup-*` 命令
3. **使用 `uv` 管理 Python 包**：自动管理虚拟环境，更快、更可靠，在项目根目录运行 `uv sync` 或 `pnpm setup-backend`
4. **添加新 Python 模块后必须运行** `pnpm setup-backend` 或 `uv sync`（在项目根目录）：这是让 PyTauri 识别新模块的必需步骤
5. **使用合理的模块结构**：
   - 相关功能放在同一个包中（如 `src-tauri/python/agents/`）
   - 每个包都要有 `__init__.py` 文件
   - 在 `tauri_app/__init__.py` 中集中导出公共接口
6. **分离模块逻辑**：
   - 数据模型定义在单独的文件中（如 `models.py`）
   - 业务逻辑在具体的处理文件中（如 `processor.py`）
   - 在 `__init__.py` 中导出这些模块
7. **编写有意义的类型注解**：使用 Pydantic 模型便于前端生成准确的 TypeScript 类型
8. **在提交前运行检查**：`pnpm lint` 和 `pnpm check-i18n`

## 相关文档

- [国际化配置](./i18n.md) - i18n 的配置和使用
- [后端设计文档](./backend.md) - Python 后端架构详情
- [前端架构](./frontend.md) - 前端项目结构和最佳实践

## 获取帮助

- 查看 Tauri 官方文档：https://tauri.app/
- PyTauri 文档：https://pytauri.github.io/pytauri/latest/
- Rust 错误解决：运行 `RUST_BACKTRACE=1 pnpm tauri dev` 查看完整堆栈跟踪
