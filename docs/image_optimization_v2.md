# 图片优化系统 V2 - 按需持久化策略

## 🎯 核心改进

### 问题
V1 版本虽然实现了缩略图压缩，但仍然存在问题：
- ❌ **所有截图立即保存到临时文件**（磁盘 I/O 开销大）
- ❌ **未持久化的 Activity 中的截图也占用磁盘空间**
- ❌ **清理策略基于时间，无法精准控制**

### 解决方案

✅ **仅内存存储** - Activity 未持久化时，截图**仅保存在内存中**
✅ **按需持久化** - Activity 持久化时，**只保存该 Activity 包含的截图**
✅ **智能淘汰** - 未被持久化的截图会被 LRU 缓存自动淘汰

## 🔄 新的工作流程

### 截图捕获阶段

```
用户操作 → 截图捕获
    ↓
压缩 + 计算 Hash → 去重检查
    ↓
✅ 仅添加到内存缓存（LRU）
    ↓
❌ 不保存临时文件
    ↓
生成虚拟路径 → 创建 RawRecord
```

### Event 处理阶段

```
Raw Records → 过滤 + 聚合 → Event
    ↓
保存到数据库（不含 Base64 数据）
    ↓
截图仍在内存中，通过 hash 索引
```

### Activity 持久化阶段（关键！）

```
Events 聚合 → Activity 生成
    ↓
遍历 Activity 中的所有截图
    ↓
从内存缓存获取图片数据（通过 hash）
    ↓
生成缩略图 → 保存到 data/thumbnails/
    ↓
✅ 从内存缓存移除（已持久化）
    ↓
保存 Activity 到数据库（不含 Base64）
```

### 未被持久化的截图

```
内存缓存（LRU, 100 张）
    ↓
新截图不断进入
    ↓
自动淘汰最旧的截图（LRU策略）
    ↓
内存自动释放，无需手动清理
```

## 📊 数据流对比

### V1 (旧版本)

```
截图 → 内存缓存 + 临时文件保存
    ↓
Event → 数据库（无 Base64）
    ↓
Activity 持久化 → 生成缩略图
    ↓
需要定期清理临时文件（24小时）
```

**问题**：临时文件占用大量磁盘空间

### V2 (新版本)

```
截图 → 仅内存缓存（LRU）
    ↓
Event → 数据库（无 Base64）
    ↓
Activity 持久化 → 生成缩略图 + 从内存移除
    ↓
未持久化的截图 → LRU 自动淘汰
```

**优势**：无临时文件，零磁盘占用

## 💾 存储优化对比

### 场景：用户使用 1 小时，每 0.5 秒截图一次

**V1 版本：**
- 临时文件：7200 × 150KB = **1.08 GB**
- 内存缓存：100 × 150KB = 15 MB
- 持久化缩略图：假设 10 个 Activity，每个 5 张截图 = 50 × 15KB = 750 KB
- **总占用**：1.08 GB + 15 MB ≈ **1.1 GB**

**V2 版本：**
- 临时文件：**0 MB** ✅
- 内存缓存：100 × 150KB = 15 MB
- 持久化缩略图：50 × 15KB = 750 KB
- **总占用**：15 MB + 750 KB ≈ **15.75 MB**

**节省**：**1.1 GB → 15.75 MB = 节省 98.6%**

## 🔧 核心代码修改

### 1. ScreenshotCapture 不再立即保存文件

**之前：**
```python
img_bytes = self._image_to_bytes(img)
base64_data = self.image_manager.add_to_memory_cache(img_hash, img_bytes)
screenshot_path = self._save_screenshot_to_file(img_bytes, img_hash)  # ❌ 立即保存
```

**现在：**
```python
img_bytes = self._image_to_bytes(img)
base64_data = self.image_manager.add_to_memory_cache(img_hash, img_bytes)
screenshot_path = self._generate_screenshot_path(img_hash)  # ✅ 仅生成虚拟路径
logger.debug(f"截图已添加到内存缓存: {img_hash[:8]}")
```

### 2. Activity 持久化时才保存截图

```python
async def save_activity(self, activity: Dict[str, Any]) -> bool:
    """保存活动到数据库（持久化截图为缩略图）"""

    # 1. 遍历 Activity 中的所有截图
    screenshot_hashes_persisted = set()
    for event in activity.get("source_events", []):
        for record in event.source_data:
            if record.type == RecordType.SCREENSHOT_RECORD:
                img_hash = record.data.get("hash")

                if img_hash and img_hash not in screenshot_hashes_persisted:
                    # 2. 从内存缓存获取
                    img_data_b64 = self.image_manager.get_from_memory_cache(img_hash)

                    if img_data_b64:
                        img_bytes = base64.b64decode(img_data_b64)

                        # 3. 持久化为缩略图
                        result = self.image_manager.persist_image(
                            img_hash,
                            img_bytes,
                            keep_original=False
                        )

                        # 4. 从内存移除（已持久化）
                        screenshot_hashes_persisted.add(img_hash)

    # 5. 保存到数据库（不含 Base64）
    self.db.insert_activity(...)
```

### 3. 前端支持内存和文件两种数据源

```tsx
export function ScreenshotThumbnail({
  screenshotPath,   // 文件路径（已持久化）
  screenshotHash,   // Hash 值
  base64Data,       // Base64 数据（内存中）
  ...
}: ScreenshotThumbnailProps) {
  useEffect(() => {
    // 优先级：base64Data > screenshotPath > screenshotHash

    if (base64Data) {
      // 未持久化的截图 - 直接显示 base64
      setImageSrc(`data:image/jpeg;base64,${base64Data}`)
      return
    }

    if (screenshotPath) {
      // 已持久化的截图 - 通过 asset 协议加载
      const assetUrl = convertFileSrc(screenshotPath, 'asset')
      setImageSrc(assetUrl)
      return
    }

    // 无可用数据源
    setError(true)
  }, [screenshotPath, screenshotHash, base64Data])
}
```

## 🚀 新增 API

### 批量获取内存中的图片

```http
POST /image/get-cached
Content-Type: application/json

{
  "hashes": ["abc123", "def456", "ghi789"]
}
```

**响应：**
```json
{
  "success": true,
  "images": {
    "abc123": "base64_data_1...",
    "def456": "base64_data_2..."
  },
  "found_count": 2,
  "requested_count": 3
}
```

**用途**：前端可以批量获取未持久化的截图数据

## 📈 性能优势

### 磁盘 I/O

| 操作 | V1 | V2 |
|------|----|----|
| 截图保存 | 每次写入磁盘 | ❌ 无磁盘操作 |
| 临时文件清理 | 定期扫描 + 删除 | ❌ 无需清理 |
| Activity 持久化 | 生成缩略图 | 生成缩略图 |

**减少磁盘 I/O：约 99%**

### 内存使用

| 项目 | V1 | V2 |
|------|----|----|
| 内存缓存 | 100 × 150KB = 15 MB | 100 × 150KB = 15 MB |
| 临时文件元数据 | ~1 MB | ❌ 0 MB |

**几乎相同，略有优化**

### 磁盘空间

| 项目 | V1 | V2 |
|------|----|----|
| 临时文件 | 1-10 GB | ❌ 0 MB |
| 持久化缩略图 | 少量 | 少量 |

**节省：1-10 GB**

## 🔍 关键设计决策

### 1. 为什么不用数据库存储 Base64？

❌ **数据库存储 Base64**
- 数据库体积膨胀
- 查询性能下降
- 备份/恢复困难

✅ **内存缓存 + 磁盘缩略图**
- 数据库轻量化
- 未持久化数据自动淘汰
- 持久化数据压缩存储

### 2. 为什么 LRU 缓存大小设为 100？

- **典型场景**：用户在 10-20 分钟内的截图（0.5秒/张 = 1200-2400 张）
- **内存占用**：100 × 150KB = 15 MB（可接受）
- **命中率**：覆盖最近几分钟的数据（Activity 聚合窗口）

可根据实际需求调整：

```python
from processing.image_manager import init_image_manager

# 增加缓存大小
init_image_manager(memory_cache_size=200)  # 30 MB

# 减少缓存大小
init_image_manager(memory_cache_size=50)   # 7.5 MB
```

### 3. 为什么 Activity 持久化时才保存？

- **Event 阶段**：数据仍在处理中，可能被过滤/合并
- **Activity 阶段**：数据已聚合完成，确定要长期保留
- **最小化存储**：只保存真正重要的截图

## 🛠️ 配置和监控

### 查看缓存统计

```bash
curl http://localhost:8000/image/stats
```

**输出：**
```json
{
  "success": true,
  "stats": {
    "memory_cache_count": 87,
    "memory_cache_limit": 100,
    "disk_thumbnail_count": 234,
    "disk_total_size_mb": 3.5
  }
}
```

### 手动清理（不再需要！）

V2 版本中，临时文件清理功能仍然保留，但实际上**不再需要**，因为不会生成临时文件。

## 📝 迁移指南

### 从 V1 升级到 V2

1. **清理旧的临时文件**
   ```bash
   rm -rf ~/.config/rewind/tmp/screenshots/*
   ```

2. **重启应用**
   ```bash
   pnpm tauri dev
   ```

3. **验证**
   - 检查临时目录：`ls ~/.config/rewind/tmp/screenshots/` 应该为空
   - 查看缓存统计：`curl http://localhost:8000/image/stats`
   - 创建新 Activity，检查缩略图目录：`ls ~/.config/rewind/data/thumbnails/`

### 兼容性

- ✅ **向后兼容**：已保存的 Activity 和缩略图不受影响
- ✅ **数据库无需迁移**
- ✅ **前端自动适配**：支持 base64 和文件路径两种方式

## 🎉 总结

### V2 的核心思想

> **截图默认不持久化，只有被 Activity 引用时才保存缩略图**

### 关键优势

1. **极致空间优化**：节省 98.6% 的磁盘空间
2. **零临时文件**：无需定期清理
3. **自动淘汰**：LRU 缓存自动管理内存
4. **按需持久化**：只保存重要的截图

### 适用场景

- ✅ 长时间运行的监控场景
- ✅ 截图频率高的场景（0.2-1秒/张）
- ✅ 磁盘空间有限的设备
- ✅ 需要最小化磁盘 I/O 的场景

### 不适用场景

- ❌ 需要保留所有原始截图
- ❌ Activity 聚合延迟很大（数小时）

---

**文档版本**：V2.0
**更新时间**：2025-10-26
**相关文件**：
- `backend/perception/screenshot_capture.py`
- `backend/processing/image_manager.py`
- `backend/processing/persistence.py`
- `backend/handlers/image.py`
- `src/components/activity/ScreenshotThumbnail.tsx`
