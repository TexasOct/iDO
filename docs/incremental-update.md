# 版本号协商增量更新系统

## 功能概述

这份文档描述了 Rewind 应用中实现的基于版本号的增量更新系统，用于高效地将后端新增的活动实时推送到前端，并支持插入动画效果。

## 系统架构

### 整体流程

```
后端保存活动
    ↓
数据库 version 字段自动递增
    ↓
发送 Tauri 事件 (activity-created)
    ↓
前端接收事件
    ↓
更新时间线状态（标记为 isNew）
    ↓
触发插入动画
```

## 实现细节

### 1. 后端实现

#### 数据库架构

**文件**: `backend/core/db.py`

- **添加 version 列**: activities 表新增 `version INTEGER DEFAULT 1` 字段
- **自动迁移**: 现有数据库会自动添加该列（向下兼容）
- **版本号递增**: 每次插入活动时，version 自动递增

**新增方法**:
```python
def get_max_activity_version(self) -> int
    """获取当前最大版本号"""

def get_activities_after_version(self, version: int, limit: int = 100) -> List
    """获取指定版本号之后的活动"""
```

#### 事件发送系统

**新文件**: `backend/core/events.py`

- **事件管理器**: 管理后端到前端的事件发送
- **事件类型**:
  - `activity-created`: 新活动创建事件
  - `activity-updated`: 活动更新事件

**注册机制**:
在 PyTauri 入口点（`src-tauri/python/rewind_app/__init__.py`）中：
```python
from rewind_backend.core.events import register_emit_handler
register_emit_handler(create_emit_handler(context))
```

#### 活动保存流程

**文件**: `backend/processing/persistence.py`

修改 `save_activity()` 方法：
1. 保存活动到数据库
2. 获取新的最大版本号
3. 发送 `activity-created` Tauri 事件到前端

#### API 接口

**新 Handler**: `get_activities_incremental`

**请求模型** (`backend/models/requests.py`):
```python
class GetActivitiesIncrementalRequest(BaseModel):
    version: int = Field(default=0)  # 客户端当前版本
    limit: int = Field(default=50)   # 最多返回数量
```

**响应格式**:
```json
{
  "success": true,
  "data": {
    "activities": [...],      // 新活动列表
    "count": 5,
    "maxVersion": 42,         // 服务器最大版本
    "clientVersion": 37       // 客户端版本
  }
}
```

### 2. 前端实现

#### 状态管理

**文件**: `src/lib/stores/activity.ts`

新增字段和方法:
```typescript
interface ActivityState {
  currentMaxVersion: number              // 客户端已同步的最大版本

  setCurrentMaxVersion(version: number)  // 更新版本号
  setTimelineData(updater)               // 更新时间线数据
}
```

#### 事件订阅 Hook

**新文件**: `src/hooks/useActivityIncremental.ts`

核心功能:
1. 订阅后端 `activity-created` 事件
2. 解析新活动数据
3. 插入到时间线（顶部）
4. 标记为 `isNew` 用于动画

**处理逻辑**:
- 如果日期存在：在顶部插入新活动
- 如果日期不存在：创建新日期块

#### 动画组件

**修改的组件**:

1. **ActivityItem** (`src/components/activity/ActivityItem.tsx`):
   - 检测 `isNew` 属性
   - 应用 `animate-in fade-in slide-in-from-top-2` CSS 动画
   - 显示 Sparkles 图标指示新活动
   - 背景变亮以突出显示

2. **TimelineDayItem** (`src/components/activity/TimelineDayItem.tsx`):
   - 检测是否有新活动或新日期
   - 应用 `animate-in fade-in slide-in-from-top-4` CSS 动画
   - 日期标题颜色变化指示新内容

3. **ActivityTimeline** (`src/components/activity/ActivityTimeline.tsx`):
   - 传递 `isNew` 标志给日期块组件

#### Activity View 集成

**修改**: `src/views/Activity/index.tsx`

```typescript
export default function ActivityView() {
  // ... 其他代码

  // 启用增量更新
  useActivityIncremental()
}
```

## 核心特性

### ✅ 版本号协商

- 后端维护活动版本号
- 前端跟踪已同步的最大版本
- 只传输增量数据

### ✅ 实时更新

- 后端活动保存时立即发送 Tauri 事件
- 前端无延迟地接收并显示

### ✅ 动画效果

- 新活动从顶部滑入淡入
- Sparkles 图标闪烁指示新内容
- 新日期块突出显示

### ✅ 跨日期边界处理

- 正确处理跨日期的新活动
- 时区问题已修复（使用本地时间）

## 使用示例

### 前端主动拉取增量更新

```typescript
import { apiClient } from '@/lib/client'

// 拉取当前版本之后的新活动
const response = await apiClient.getActivitiesIncremental({
  version: currentMaxVersion,
  limit: 50
})

console.log(`新活动: ${response.data.count}`)
console.log(`服务器版本: ${response.data.maxVersion}`)
```

### 后端自动推送更新

当处理管道保存新活动时，自动发送事件：

```typescript
// 前端
useActivityIncremental()  // hook 自动订阅和处理

// 后端
await persistence.save_activity(activity)  // 自动发送事件
```

## 性能考虑

### 优势

1. **带宽优化**: 只传输版本之后的新数据
2. **实时性**: Tauri 事件推送不依赖轮询
3. **可扩展**: 支持大量历史数据且查询高效

### 限制

- 一次最多返回 100 条新活动（可配置）
- 版本号存储为 INTEGER（足够用于 21 亿+ 条记录）

## 故障排除

### 事件未收到

1. 检查后端是否成功调用 `emit_activity_created()`
2. 验证 PyTauri context 已正确注册
3. 检查前端是否正确导入 `useActivityIncremental()`

### 动画不显示

1. 确保 Tailwind CSS 的 `animate-in` 类已启用
2. 检查浏览器控制台的动画相关警告
3. 验证 `isNew` 标记是否正确传递

### 版本号不同步

1. 在 Activity View 挂载时重置版本号 (`currentMaxVersion = 0`)
2. 检查数据库版本号是否持续递增
3. 使用 `getActivitiesIncremental` API 验证版本号逻辑

## 扩展方向

### 未来改进

1. **批量操作**: 支持批量推送多个活动
2. **部分更新**: 支持活动字段的增量更新（不仅限新增）
3. **清理策略**: 定期清理旧版本号避免溢出
4. **持久化版本**: 在本地存储中保存版本号用于离线支持

## 相关文件列表

**后端**:
- `backend/core/db.py` - 数据库版本管理
- `backend/core/events.py` - 事件发送系统
- `backend/processing/persistence.py` - 活动保存和事件发送
- `backend/handlers/processing.py` - 增量查询 API
- `backend/models/requests.py` - 请求模型
- `src-tauri/python/rewind_app/__init__.py` - PyTauri 入口点

**前端**:
- `src/lib/stores/activity.ts` - 状态管理
- `src/hooks/useActivityIncremental.ts` - 事件订阅和增量更新
- `src/components/activity/ActivityItem.tsx` - 活动项动画
- `src/components/activity/TimelineDayItem.tsx` - 日期块动画
- `src/components/activity/ActivityTimeline.tsx` - 时间线容器
- `src/views/Activity/index.tsx` - Activity 页面集成
