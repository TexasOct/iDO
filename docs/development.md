# 开发环境配置指南

本文档介绍如何配置 Rewind 项目的开发环境，包括前端和 Python 后端的设置。

## 项目结构概览

```
rewind/
├── src/                    # 前端 React 代码
├── src-tauri/             # Tauri 应用配置
│   ├── python/            # Python 后端代码（PyTauri）
│   ├── src/               # Rust 代码
│   ├── Cargo.toml         # Rust 依赖
│   └── pyproject.toml     # Python 项目配置
├── package.json           # Node.js 依赖
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

### 1. 使用 uv 创建虚拟环境

```bash
# 进入 Tauri 目录
cd src-tauri

# 使用 uv 创建虚拟环境
uv venv
```

这将在 `src-tauri` 目录下创建 `.venv` 目录。

### 2. 激活虚拟环境

**macOS / Linux:**

```bash
source .venv/bin/activate
```

**Windows:**

```bash
.venv\Scripts\activate
```

### 3. 安装 Python 依赖

```bash
# 确保虚拟环境已激活
# 使用 uv 安装依赖
uv pip install -e src-tauri
```

或者使用传统的 pip：

```bash
pip install -e src-tauri
```

这将安装 `pyproject.toml` 中定义的所有依赖。

### 4. Python 依赖说明

项目的 Python 依赖定义在 `src-tauri/pyproject.toml`：

```toml
[project]
name = "tauri-app"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
    "pytauri == 0.8.*",    # Python-Rust 桥梁
    "pydantic == 2.*",     # 数据验证
    "anyio == 4.*"         # 异步 I/O
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

修改完 Python 代码后，需要重新安装包以使新模块生效：

```bash
# 从项目根目录运行，激活虚拟环境后执行
uv pip install -e src-tauri
```

或者使用 pip：

```bash
pip install -e src-tauri
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

如果新模块需要额外的 Python 包，编辑 `src-tauri/pyproject.toml`：

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

然后重新安装：

```bash
uv pip install -e src-tauri
```

## 完整的开发工作流

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

# 或者在虚拟环境中直接测试 Python 代码
cd src-tauri
source .venv/bin/activate
python -m tauri_app
```

#### 如果添加了新的 Python 模块或修改了 pyproject.toml

```bash
# 1. 创建新的 Python 模块（参考 7. 添加新的 Python 模块）
# 2. 更新项目（重要步骤！）
uv pip install -e src-tauri

# 3. 重新生成 TypeScript 客户端
pnpm tauri dev

# 或手动重建
cd src-tauri
cargo build
```

**注意**: 添加新模块或添加新依赖后必须运行 `uv pip install -e src-tauri`，否则 PyTauri 无法识别新模块。

## 环境变量配置

项目支持以下环境变量（可选）：

```bash
# 指定 Python 可执行文件位置（一般不需要）
export PYTHON_EXECUTABLE=/usr/bin/python3

# 启用详细日志
export RUST_LOG=debug
```

## 常见问题

### Q: 如何查看虚拟环境是否激活？

A: 在命令行提示符中应该看到 `(.venv)` 前缀：

```bash
(.venv) $ python --version
Python 3.13.0
```

### Q: 如何重置虚拟环境？

A: 删除并重新创建：

```bash
# 删除旧环境
rm -rf .venv

# 重新创建
uv venv
source .venv/bin/activate  # 或在 Windows 中使用 .venv\Scripts\activate
uv pip install -e .
```

### Q: 启动 `pnpm tauri dev` 时出现 Python 错误？

A: 确保：

1. 虚拟环境已激活
2. Python 依赖已正确安装：`uv pip install -e .`
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
3. **运行了** `uv pip install -e src-tauri` 来更新项目（这是最常被遗漏的步骤！）
4. 重新运行 `pnpm tauri dev` 来重新生成 TypeScript 客户端

如果还是看不到，尝试：

```bash
# 完整的重建流程
cd src-tauri
uv pip install -e .  # 从 src-tauri 目录重新安装
cargo clean          # 清理 Rust 缓存
cd ..
pnpm tauri dev      # 重新启动应用
```

### Q: 如何在不启动 Tauri 的情况下测试 Python 代码？

A: 在虚拟环境中直接运行：

```bash
cd src-tauri
source .venv/bin/activate  # 或在 Windows 中使用 .venv\Scripts\activate
python -c "from myfeature.processor import process_data; import asyncio; print(asyncio.run(process_data({'test': 'data'})))"
```

或创建一个测试脚本 `test_my_module.py`：

```python
import asyncio
from myfeature.processor import process_data

async def main():
    result = await process_data({'test': 'data'})
    print(result)

if __name__ == '__main__':
    asyncio.run(main())
```

然后运行：

```bash
python test_my_module.py
```

## 最佳实践

1. **始终使用虚拟环境**：确保 Python 依赖隔离
2. **激活虚拟环境后运行 Tauri 开发命令**：确保使用正确的 Python 环境
3. **定期同步依赖**：当 `package.json` 或 `pyproject.toml` 变更时，重新运行安装命令
4. **使用 `uv` 管理 Python 包**：更快、更可靠
5. **添加新 Python 模块后必须运行** `uv pip install -e src-tauri`：这是让 PyTauri 识别新模块的必需步骤
6. **使用合理的模块结构**：
   - 相关功能放在同一个包中（如 `src-tauri/python/agents/`）
   - 每个包都要有 `__init__.py` 文件
   - 在 `tauri_app/__init__.py` 中集中导出公共接口
7. **分离模块逻辑**：
   - 数据模型定义在单独的文件中（如 `models.py`）
   - 业务逻辑在具体的处理文件中（如 `processor.py`）
   - 在 `__init__.py` 中导出这些模块
8. **编写有意义的类型注解**：使用 Pydantic 模型便于前端生成准确的 TypeScript 类型
9. **在提交前运行检查**：`pnpm lint` 和 `pnpm check-i18n`

## 相关文档

- [国际化配置](./i18n.md) - i18n 的配置和使用
- [后端设计文档](./backend.md) - Python 后端架构详情
- [前端架构](./frontend.md) - 前端项目结构和最佳实践

## 获取帮助

- 查看 Tauri 官方文档：https://tauri.app/
- PyTauri 文档：https://pytauri.github.io/pytauri/latest/
- Rust 错误解决：运行 `RUST_BACKTRACE=1 pnpm tauri dev` 查看完整堆栈跟踪
