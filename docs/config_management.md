# 配置管理系统

## 概述

Rewind 的配置系统已重构为**文件直接编辑模式**，将配置从数据库迁移到 `~/.config/rewind/config.toml`。

## 配置文件位置

### 优先级
1. **用户配置目录**（优先）: `~/.config/rewind/config.toml`
2. **项目目录**（开发）: `backend/config/config.toml`

### 自动创建
如果 `~/.config/rewind/config.toml` 不存在，应用启动时会自动创建一个包含所有默认值的配置文件。

## 配置文件内容

### 服务器配置
```toml
[server]
host = "0.0.0.0"
port = 8000
debug = false
```

### 数据库配置
```toml
[database]
# 数据库存储位置（支持绝对路径）
path = "~/.config/rewind/rewind.db"
```

### 截图配置
```toml
[screenshot]
# 截图存储位置（支持绝对路径）
save_path = "~/.config/rewind/screenshots"
```

### LLM 配置
```toml
[llm]
default_provider = "openai"

[llm.openai]
api_key = "your_api_key_here"
model = "gpt-4"
base_url = "https://api.openai.com/v1"

[llm.qwen3vl]
api_key = "your_api_key_here"
model = "qwen-vl-max"
base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
```

### 监控配置
```toml
[monitoring]
window_size = 20           # 滑动窗口大小（秒）
capture_interval = 0.2     # 捕获间隔（秒）
processing_interval = 10   # 处理间隔（秒）
```

## Settings 管理器

Settings 管理器现在直接编辑 `config.toml` 文件，而不是使用数据库表。

### 使用方式

```python
from backend.core.settings import get_settings
from backend.config.loader import get_config

# 初始化
config_loader = get_config()
config_loader.load()

from backend.core.settings import init_settings
init_settings(config_loader)

# 获取 Settings
settings = get_settings()

# 获取配置
db_path = settings.get_database_path()
screenshot_path = settings.get_screenshot_path()
llm_settings = settings.get_llm_settings()

# 更新配置（实时保存到 config.toml）
settings.set_database_path("/new/path/to/rewind.db")
settings.set_screenshot_path("/new/path/to/screenshots")
settings.set_llm_settings(
    provider="openai",
    api_key="new_key",
    model="gpt-4-turbo",
    base_url="https://api.openai.com/v1"
)

# 获取任意配置项
value = settings.get("llm.default_provider")

# 设置任意配置项
settings.set("monitoring.window_size", 30)

# 获取所有配置
all_config = settings.get_all()

# 重新加载配置文件
settings.reload()
```

## 数据库路径切换

当用户在前端 Settings 页面修改数据库路径时，系统会：

1. 保存新路径到 `config.toml`
2. **立即切换**到新的数据库（不需要重启）
3. 后续所有数据库操作都使用新路径

```python
# 这会触发立即切换
settings.set_database_path("/new/database/path/rewind.db")
```

## 前端集成

### Settings 页面

前端 Settings 页面现在编辑的是 `~/.config/rewind/config.toml` 中的配置：

```typescript
// 获取当前配置
const settings = await getSettingsInfo()

// 更新配置
await updateSettings({
  llm: {
    provider: "openai",
    api_key: "new_key",
    model: "gpt-4",
    base_url: "https://api.openai.com/v1"
  },
  database_path: "/new/path/to/rewind.db",
  screenshot_save_path: "/new/path/to/screenshots"
})
```

## 配置加载流程

```
应用启动
  ↓
ConfigLoader._get_default_config_file()
  ├─ 检查 ~/.config/rewind/config.toml (优先)
  └─ 检查项目内 backend/config/config.toml (开发)
  ↓
配置文件不存在？
  ├─ YES: 自动创建默认配置到 ~/.config/rewind/config.toml
  └─ NO: 加载现有配置
  ↓
ConfigLoader.load()
  └─ 解析 TOML 文件，环境变量替换
  ↓
init_settings(config_loader)
  └─ 初始化 Settings 管理器
  ↓
get_database_path() from config.toml
  └─ 初始化数据库
```

## 迁移指南（从数据库配置到文件配置）

### 对用户
- **无需操作** - 所有配置仍然通过前端 Settings 页面编辑
- 配置现在保存在 `~/.config/rewind/config.toml` 而不是数据库

### 对开发者
1. 移除了 `backend/core/settings.py` 中的数据库依赖
2. 配置直接读写 `config.toml` 文件
3. `backend/core/db.py` 不再有 `settings` 表相关代码
4. `ConfigLoader` 添加了 `set()` 和 `save()` 方法支持写入

## 常见问题

### Q: 配置文件在哪里？
**A:** 默认位置是 `~/.config/rewind/config.toml`

### Q: 如何重置为默认配置？
**A:** 删除 `~/.config/rewind/config.toml`，应用重启时会自动创建新的默认配置

### Q: 配置改变后需要重启应用吗？
**A:** 不需要！Settings 中的更改会立即生效（特别是数据库路径）

### Q: 项目内的 config.toml 有什么用？
**A:** 作为开发环境的备份配置，用户配置优先级更高

### Q: 可以同时编辑 config.toml 和前端 Settings 吗？
**A:** 可以，但要避免同时修改。Settings 对象会实时读取文件内容

## 技术细节

### ConfigLoader 新增方法
- `set(key, value)` - 设置配置值（支持点号分隔的嵌套键）
- `save()` - 保存配置到文件
- `_create_default_config()` - 创建默认配置文件

### SettingsManager 现在
- 不再需要数据库依赖
- 直接操作 ConfigLoader
- 保留相同的 API 接口（向后兼容）

## 修改历史

### 2025-10-25
- ✅ 实现 ConfigLoader 的自动创建功能
- ✅ 添加 set/save 方法支持配置写入
- ✅ 重写 SettingsManager 移除数据库依赖
- ✅ 更新启动流程使用新的配置系统
- ✅ 实现数据库路径即时切换功能
