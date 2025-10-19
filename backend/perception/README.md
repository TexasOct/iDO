# Perception 模块

Perception 模块是 Rewind Backend 的感知层，负责实时捕获用户的键盘、鼠标操作和屏幕截图。

## 功能特性

- **键盘事件捕获**: 监控键盘输入，特别关注特殊键和组合键
- **鼠标事件捕获**: 监控鼠标点击、拖拽、滚动等操作
- **屏幕截图捕获**: 定期截取屏幕内容，支持压缩和去重
- **滑动窗口存储**: 20秒临时存储，自动清理过期数据
- **异步任务管理**: 协调多个捕获器的异步运行

## 模块结构

```
perception/
├── base.py              # 基础抽象类
├── keyboard_capture.py  # 键盘事件捕获
├── mouse_capture.py     # 鼠标事件捕获
├── screenshot_capture.py # 屏幕截图捕获
├── storage.py           # 滑动窗口存储
├── manager.py           # 异步任务管理器
└── README.md           # 本文档
```

## 快速开始

### 基本使用

```python
import asyncio
from perception.manager import PerceptionManager

async def main():
    # 创建感知管理器
    manager = PerceptionManager(
        capture_interval=0.2,  # 每0.2秒截图一次
        window_size=20,        # 20秒滑动窗口
        on_data_captured=on_data_captured  # 数据捕获回调
    )
    
    # 启动管理器
    await manager.start()
    
    # 运行一段时间
    await asyncio.sleep(30)
    
    # 停止管理器
    await manager.stop()

def on_data_captured(record):
    """处理捕获的数据"""
    print(f"捕获到事件: {record.type.value} - {record.data}")

# 运行
asyncio.run(main())
```

### 单独使用捕获器

```python
from perception.keyboard_capture import KeyboardCapture
from perception.mouse_capture import MouseCapture
from perception.screenshot_capture import ScreenshotCapture

# 键盘捕获
keyboard = KeyboardCapture(on_event=handle_keyboard)
keyboard.start()

# 鼠标捕获
mouse = MouseCapture(on_event=handle_mouse)
mouse.start()

# 屏幕截图捕获
screenshot = ScreenshotCapture(on_event=handle_screenshot)
screenshot.start()

# 停止捕获
keyboard.stop()
mouse.stop()
screenshot.stop()
```

## API 接口

### 启动/停止感知模块

```bash
# 启动感知模块
curl -X POST http://localhost:8000/perception/start

# 停止感知模块
curl -X POST http://localhost:8000/perception/stop
```

### 获取统计信息

```bash
# 获取感知模块统计
curl http://localhost:8000/perception/stats
```

### 获取记录数据

```bash
# 获取所有记录
curl http://localhost:8000/perception/records

# 获取键盘事件
curl http://localhost:8000/perception/records/keyboard

# 获取鼠标事件
curl http://localhost:8000/perception/records/mouse

# 获取屏幕截图
curl http://localhost:8000/perception/records/screenshots
```

### 清空记录

```bash
# 清空所有记录
curl -X DELETE http://localhost:8000/perception/records
```

## 配置选项

### PerceptionManager 参数

- `capture_interval`: 屏幕截图捕获间隔（秒），默认 0.2
- `window_size`: 滑动窗口大小（秒），默认 20
- `on_data_captured`: 数据捕获回调函数

### 屏幕截图配置

```python
# 设置压缩参数
manager.set_compression_settings(
    quality=85,      # JPEG 质量 (1-100)
    max_width=1920,  # 最大宽度
    max_height=1080  # 最大高度
)
```

## 数据格式

### 键盘事件

```json
{
    "timestamp": "2024-01-01T12:00:00.000Z",
    "type": "keyboard_event",
    "data": {
        "action": "press",
        "key": "enter",
        "key_type": "special",
        "modifiers": ["ctrl"],
        "timestamp": "2024-01-01T12:00:00.000Z"
    }
}
```

### 鼠标事件

```json
{
    "timestamp": "2024-01-01T12:00:00.000Z",
    "type": "mouse_event",
    "data": {
        "action": "click",
        "button": "left",
        "position": [100, 200],
        "timestamp": "2024-01-01T12:00:00.000Z"
    }
}
```

### 屏幕截图

```json
{
    "timestamp": "2024-01-01T12:00:00.000Z",
    "type": "screenshot",
    "data": {
        "action": "capture",
        "width": 1920,
        "height": 1080,
        "format": "JPEG",
        "size_bytes": 150000,
        "hash": "abc123...",
        "monitor": {"left": 0, "top": 0, "width": 1920, "height": 1080},
        "timestamp": "2024-01-01T12:00:00.000Z"
    }
}
```

## 演示脚本

运行演示脚本来查看 perception 模块的实际效果：

```bash
cd /Users/icyfeather/Projects/Rewind/backend
uv run python scripts/demo_perception.py
```

## 测试

运行测试套件：

```bash
cd /Users/icyfeather/Projects/Rewind/backend
uv run pytest tests/test_perception.py -v
```

## 注意事项

1. **权限要求**: 在某些系统上，捕获键盘和鼠标事件可能需要特殊权限
2. **性能影响**: 屏幕截图会消耗一定的 CPU 和内存资源
3. **隐私保护**: 确保在适当的隐私保护措施下使用此模块
4. **平台兼容性**: 目前主要支持 macOS，其他平台可能需要额外配置

## 故障排除

### 常见问题

1. **无法捕获键盘/鼠标事件**
   - 检查系统权限设置
   - 确保应用有输入监控权限

2. **屏幕截图失败**
   - 检查显示器配置
   - 确保 mss 库正确安装

3. **内存使用过高**
   - 减少 `window_size` 参数
   - 降低屏幕截图质量
   - 增加清理频率

### 调试模式

启用详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 扩展开发

### 添加新的捕获器

1. 继承 `BaseCapture` 类
2. 实现 `capture()` 和 `output()` 方法
3. 在 `PerceptionManager` 中集成

### 自定义数据处理

实现自定义的数据处理逻辑：

```python
def custom_data_processor(record):
    # 自定义数据处理逻辑
    if record.type == EventType.KEYBOARD_EVENT:
        # 处理键盘事件
        pass
    elif record.type == EventType.MOUSE_EVENT:
        # 处理鼠标事件
        pass

manager = PerceptionManager(on_data_captured=custom_data_processor)
```
