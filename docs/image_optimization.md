# 图片优化系统

## 概述

Rewind 实现了一套完整的图片优化系统，用于管理截屏事件的存储和缓存。该系统采用分层策略：
- **内存缓存** - 未持久化的活动中的截图保存在内存中
- **缩略图持久化** - 持久化的活动只保存压缩后的缩略图
- **自动清理** - 定期清理过期的临时文件

## 架构设计

### 1. ImageManager (图片管理器)

位置：`backend/processing/image_manager.py`

#### 主要功能

- **内存缓存管理**
  - LRU 缓存策略（使用 OrderedDict）
  - 可配置缓存大小（默认 100 张图片）
  - Base64 编码存储，减少重复编码开销

- **缩略图生成**
  - 默认尺寸：400×225 (16:9)
  - 质量：75% JPEG
  - 使用 PIL/Pillow 的 LANCZOS 算法保证质量

- **智能持久化**
  - 仅在 Activity 持久化时才生成缩略图
  - 去重：相同 hash 的图片只持久化一次
  - 可选保留原图（默认关闭）

- **自动清理**
  - 基于文件修改时间
  - 可配置保留期限（默认 24 小时）
  - 提供手动清理 API

#### 配置参数

```python
from processing.image_manager import init_image_manager

init_image_manager(
    memory_cache_size=100,           # 内存缓存大小
    thumbnail_size=(400, 225),       # 缩略图尺寸
    thumbnail_quality=75,            # JPEG 质量 (1-100)
    max_age_hours=24                 # 最大保留时间
)
```

### 2. 截屏捕获集成

位置：`backend/perception/screenshot_capture.py`

#### 工作流程

```
捕获截图 → 压缩/调整大小 → 计算 Hash → 去重检查
    ↓
添加到内存缓存 → 保存临时文件 → 创建 RawRecord
    ↓
移除 Base64 数据（仅保留路径） → 发送事件
```

#### 优化点

1. **自动缓存**：所有截图自动添加到内存缓存
2. **延迟持久化**：临时文件保存在 `tmp/screenshots/`
3. **内存优化**：RawRecord 不再存储 `image_data` 字段

### 3. 持久化策略

位置：`backend/processing/persistence.py`

#### Event 持久化

```python
async def save_event(self, event: Event) -> bool:
    # 移除截图的 Base64 数据
    # 只保留 hash 和路径信息
    # 截图仍在内存缓存中
```

#### Activity 持久化

```python
async def save_activity(self, activity: Dict[str, Any]) -> bool:
    # 1. 遍历所有截图
    # 2. 从内存缓存获取图片数据
    # 3. 生成并保存缩略图
    # 4. 从内存缓存移除（已持久化）
    # 5. 保存到数据库（不含 Base64）
```

#### 数据流向

```
RawRecord (内存缓存 + 临时文件)
    ↓
Event (内存缓存，数据库无 Base64)
    ↓
Activity 持久化
    ↓
生成缩略图 → 保存到 data/thumbnails/
    ↓
从内存缓存移除 → 数据库（无 Base64）
    ↓
删除临时文件（定期清理）
```

## API 接口

### 获取图片统计

```http
GET /image/stats
```

**响应示例：**
```json
{
  "success": true,
  "stats": {
    "memory_cache_count": 45,
    "memory_cache_limit": 100,
    "disk_thumbnail_count": 234,
    "disk_total_size_mb": 12.5,
    "thumbnail_size": [400, 225],
    "thumbnail_quality": 75
  }
}
```

### 清理旧图片

```http
POST /image/cleanup
Content-Type: application/json

{
  "maxAgeHours": 24
}
```

**响应示例：**
```json
{
  "success": true,
  "cleaned_count": 15,
  "message": "已清理 15 个旧图片文件"
}
```

### 清空内存缓存

```http
POST /image/clear-cache
```

**响应示例：**
```json
{
  "success": true,
  "cleared_count": 45,
  "message": "已清空 45 个内存缓存的图片"
}
```

## 前端集成

### ScreenshotThumbnail 组件

位置：`src/components/activity/ScreenshotThumbnail.tsx`

#### 使用方式

```tsx
import { ScreenshotThumbnail } from './ScreenshotThumbnail'

// 在 RecordItem 中使用
<ScreenshotThumbnail
  screenshotPath={metadata.screenshotPath}
  width={280}
  height={160}
/>
```

#### 工作原理

1. 使用 Tauri 的 `convertFileSrc` 转换本地路径
2. 支持加载状态和错误处理
3. 懒加载优化性能
4. 鼠标悬浮效果

### 配置要求

**tauri.conf.json:**
```json
{
  "app": {
    "security": {
      "csp": "default-src 'self' ipc: http://ipc.localhost; img-src 'self' asset: http://asset.localhost data:; ...",
      "assetProtocol": {
        "enable": true,
        "scope": {
          "allow": ["$HOME/.config/rewind/**"],
          "deny": []
        }
      }
    }
  }
}
```

## 性能优势

### 空间优化

以 1920×1080 的截图为例：

| 阶段 | 原始大小 | 优化后大小 | 节省比例 |
|------|---------|-----------|---------|
| 原始截图 | ~500 KB | 压缩到 ~150 KB | 70% |
| 持久化缩略图 | ~150 KB | ~15 KB | 90% |
| **总节省** | **500 KB** | **15 KB** | **97%** |

### 时间优化

- **内存缓存命中**：< 1ms
- **Base64 编码复用**：避免重复编码
- **异步持久化**：不阻塞主流程

### 内存优化

- **LRU 缓存**：自动淘汰最少使用的图片
- **限制大小**：默认最多 100 张（约 15 MB）
- **及时释放**：持久化后立即从缓存移除

## 维护指南

### 手动清理

```bash
# 使用 FastAPI 测试
curl -X POST http://localhost:8000/image/cleanup \
  -H "Content-Type: application/json" \
  -d '{"maxAgeHours": 12}'
```

### 监控统计

```bash
# 获取缓存统计
curl http://localhost:8000/image/stats
```

### 定期任务建议

建议在 coordinator 中添加定期清理任务：

```python
# 在 core/coordinator.py 中
import asyncio
from processing.image_manager import get_image_manager

async def periodic_cleanup():
    """每小时清理一次旧图片"""
    while True:
        await asyncio.sleep(3600)  # 1 小时
        image_manager = get_image_manager()
        cleaned = image_manager.cleanup_old_files()
        logger.info(f"定期清理：删除 {cleaned} 个旧图片")
```

## 故障排查

### 图片无法显示

1. **检查 Tauri 配置**
   - 确认 `assetProtocol.enable = true`
   - 确认 CSP 包含 `asset:` 和 `http://asset.localhost`

2. **检查文件权限**
   ```bash
   ls -la ~/.config/rewind/tmp/screenshots/
   ```

3. **查看控制台日志**
   - 检查 `[ScreenshotThumbnail]` 开头的日志
   - 确认 `convertFileSrc` 的转换结果

### 磁盘空间占用过大

1. **检查统计信息**
   ```bash
   curl http://localhost:8000/image/stats
   ```

2. **手动清理**
   ```bash
   curl -X POST http://localhost:8000/image/cleanup \
     -H "Content-Type: application/json" \
     -d '{"maxAgeHours": 6}'
   ```

3. **调整缩略图质量**
   ```python
   init_image_manager(thumbnail_quality=60)  # 降低质量
   ```

### 内存占用过高

1. **减少缓存大小**
   ```python
   init_image_manager(memory_cache_size=50)
   ```

2. **清空缓存**
   ```bash
   curl -X POST http://localhost:8000/image/clear-cache
   ```

## 未来优化方向

1. **WebP 格式**：更好的压缩比
2. **渐进式加载**：先显示模糊图，再加载高清图
3. **CDN 集成**：支持云端存储
4. **智能压缩**：根据内容动态调整质量
5. **批量操作**：批量生成缩略图提高效率

## 相关文件

- `backend/processing/image_manager.py` - 图片管理器核心
- `backend/perception/screenshot_capture.py` - 截屏捕获集成
- `backend/processing/persistence.py` - 持久化策略
- `backend/handlers/image.py` - API 接口
- `src/components/activity/ScreenshotThumbnail.tsx` - 前端组件
- `src/components/activity/RecordItem.tsx` - 截屏渲染
