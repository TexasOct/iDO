# 前端架构

本文档详细说明了 iDO 前端系统的架构设计、组件结构、状态管理以及数据同步机制。

## 目录

- [架构概览](#架构概览)
- [项目结构](#项目结构)
- [组件架构](#组件架构)
- [状态管理](#状态管理)
- [数据同步](#数据同步)
- [路由和菜单](#路由和菜单)
- [最佳实践](#最佳实践)

## 架构概览

iDO 前端采用现代化的 React 架构，包含以下特点：

- **React 19 + TypeScript 5**：最新的 React 特性和完整的类型安全
- **Zustand 状态管理**：轻量级但功能强大的全局状态管理
- **服务层模式**：所有 API 调用通过服务层抽象
- **Tauri 集成**：无缝调用后端 Python 功能
- **实时更新**：通过 Tauri 事件实现前后端同步

### 数据流

```
┌─────────────────────────────────────────────────────────────┐
│                      User Action                            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│              Component Event Handler                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│              Zustand Store Action                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│              Service Layer (API Wrapper)                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│              PyTauri Client                                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓
┌─────────────────────────────────────────────────────────────┐
│              Python Backend                                 │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        │                         │
        ↓                         ↓
┌────────────────┐      ┌─────────────────┐
│ Database       │      │ Tauri Event     │
│ Response       │      │ Broadcast       │
└────────┬───────┘      └────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ↓
        ┌────────────────────────┐
        │  Zustand Store Update  │
        └────────────┬───────────┘
                     │
                     ↓
        ┌────────────────────────┐
        │  Component Re-render   │
        └────────────────────────┘
```

## 项目结构

### 完整目录树

```
src/
├── views/                          # 页面级组件（路由目标）
│   ├── Activity/                  # 活动时间线
│   │   └── index.tsx
│   ├── Dashboard/                 # 仪表板
│   │   └── index.tsx
│   ├── Agents/                    # Agent 任务管理
│   │   └── index.tsx
│   └── Settings/                  # 设置页面
│       └── index.tsx
│
├── layouts/                        # 布局组件
│   ├── MainLayout.tsx            # 主应用布局
│   └── AuthLayout.tsx            # 认证布局
│
├── components/                     # 可复用组件
│   ├── Activity/                  # 活动相关组件
│   │   ├── ActivityTimeline.tsx
│   │   └── ActivityItem.tsx
│   ├── Agents/                    # Agent 相关组件
│   │   ├── TaskList.tsx
│   │   └── TaskItem.tsx
│   ├── Dashboard/                 # 仪表板组件
│   │   ├── StatsCard.tsx
│   │   └── Chart.tsx
│   └── Common/                    # 通用组件
│       ├── Header.tsx
│       ├── Sidebar.tsx
│       └── Navigation.tsx
│
├── lib/
│   ├── stores/                    # Zustand 状态管理
│   │   ├── activity.ts           # 活动数据 store
│   │   ├── agents.ts             # Agent 数据 store
│   │   ├── dashboard.ts          # 仪表板数据 store
│   │   ├── settings.ts           # 设置 store
│   │   ├── ui.ts                 # UI 状态 store
│   │   └── index.ts              # 导出
│   │
│   ├── services/                  # API 服务层
│   │   ├── activity/
│   │   │   └── index.ts          # 活动相关 API
│   │   ├── agents/
│   │   │   └── index.ts          # Agent 相关 API
│   │   ├── system/
│   │   │   └── index.ts          # 系统 API
│   │   └── index.ts              # 导出
│   │
│   ├── types/                     # TypeScript 类型定义
│   │   ├── activity.ts
│   │   ├── agents.ts
│   │   ├── system.ts
│   │   └── index.ts
│   │
│   ├── config/                    # 配置文件
│   │   ├── menu.ts               # 菜单配置
│   │   ├── constants.ts          # 常量定义
│   │   └── index.ts
│   │
│   ├── client/                    # 自动生成的 PyTauri 客户端
│   │   └── (DO NOT EDIT)
│   │
│   └── hooks/                     # 自定义 React hooks
│       ├── useActivityStore.ts
│       ├── useActivityIncremental.ts
│       ├── useInfiniteScroll.ts
│       └── ...
│
└── locales/                        # i18n 翻译文件
    ├── en.ts                      # 英文
    └── zh-CN.ts                   # 中文
```

## 组件架构

### 组件分层

```
┌──────────────────────────────────────────┐
│           Page Component                 │
│     (src/views/Activity/index.tsx)       │
│  • 数据获取和初始化                      │
│  • 全局状态管理                          │
│  • 路由参数处理                          │
└──────────────────┬───────────────────────┘
                   │
    ┌──────────────┴──────────────┐
    │                             │
┌───┴─────────────────┐   ┌──────┴──────────────┐
│  Container Component │   │  Container Component │
│ (ActivityTimeline)  │   │ (ActivitySidebar)    │
│ • 业务逻辑           │   │ • 业务逻辑           │
│ • 状态订阅           │   │ • 状态订阅           │
│ • 事件处理           │   │ • 事件处理           │
└───┬─────────────────┘   └──────┬──────────────┘
    │                            │
    └──────────────┬─────────────┘
                   │
    ┌──────────────┴──────────────┐
    │                             │
┌───┴─────────────────┐   ┌──────┴──────────────┐
│  Presentation       │   │  Presentation      │
│  Component          │   │  Component         │
│  (ActivityItem)     │   │  (FilterControl)   │
│  • 纯UI展示         │   │  • 纯UI展示        │
│  • Props 驱动       │   │  • Props 驱动      │
│  • React.memo优化  │   │  • React.memo优化  │
└─────────────────────┘   └────────────────────┘
```

### 典型页面组件示例

```typescript
// src/views/Activity/index.tsx
import { useEffect, useState } from 'react'
import { useActivityStore } from '@/lib/stores'
import { ActivityTimeline } from '@/components/Activity'

export default function ActivityView() {
  // 订阅全局状态
  const timelineData = useActivityStore((state) => state.timelineData)
  const loading = useActivityStore((state) => state.loading)
  const fetchActivityTimeline = useActivityStore((state) => state.fetchActivityTimeline)

  // 初始化加载
  useEffect(() => {
    fetchActivityTimeline()
  }, [fetchActivityTimeline])

  return (
    <div>
      {loading ? <LoadingSpinner /> : <ActivityTimeline data={timelineData} />}
    </div>
  )
}
```

### 容器组件示例

```typescript
// src/components/Activity/ActivityTimeline.tsx
import { useCallback } from 'react'
import { useActivityStore } from '@/lib/stores'
import { ActivityItem } from './ActivityItem'

interface ActivityTimelineProps {
  data: Activity[]
}

export function ActivityTimeline({ data }: ActivityTimelineProps) {
  const updateActivity = useActivityStore((state) => state.updateActivity)

  const handleActivityClick = useCallback((activityId: string) => {
    // 业务逻辑
    updateActivity(activityId)
  }, [updateActivity])

  return (
    <div>
      {data.map((activity) => (
        <ActivityItem
          key={activity.id}
          activity={activity}
          onClick={handleActivityClick}
        />
      ))}
    </div>
  )
}
```

### 展示组件示例

```typescript
// src/components/Activity/ActivityItem.tsx
import { memo } from 'react'
import { Activity } from '@/lib/types'

interface ActivityItemProps {
  activity: Activity
  onClick: (id: string) => void
}

export const ActivityItem = memo(function ActivityItem({
  activity,
  onClick,
}: ActivityItemProps) {
  return (
    <div onClick={() => onClick(activity.id)}>
      <h3>{activity.name}</h3>
      <p>{activity.description}</p>
      <time>{new Date(activity.timestamp).toLocaleString()}</time>
    </div>
  )
})
```

## 状态管理

### Zustand Store 概览

iDO 使用多个 Zustand store 来管理不同的应用状态。

```typescript
// src/lib/stores/index.ts
export { useActivityStore } from './activity'
export { useAgentsStore } from './agents'
export { useDashboardStore } from './dashboard'
export { useSettingsStore } from './settings'
export { useUIStore } from './ui'
```

### Activity Store

管理活动时间线数据。

```typescript
// src/lib/stores/activity.ts
interface ActivityState {
  // 数据
  timelineData: Activity[]
  currentMaxVersion: number

  // UI 状态
  loading: boolean
  isRefreshing: boolean
  loadingMore: boolean
  expandedItems: Set<string>

  // 分页
  topOffset: string | null
  bottomOffset: string | null

  // 操作
  fetchActivityTimeline: () => Promise<void>
  fetchActivitiesIncremental: () => Promise<void>
  updateActivity: (id: string, updates: Partial<Activity>) => void
  deleteActivity: (id: string) => void
  setExpandedItems: (items: Set<string>) => void
}

export const useActivityStore = create<ActivityState>(
  persist(
    (set, get) => ({
      timelineData: [],
      currentMaxVersion: 0,
      loading: false,
      isRefreshing: false,
      loadingMore: false,
      expandedItems: new Set(),
      topOffset: null,
      bottomOffset: null,

      fetchActivityTimeline: async () => {
        set({ loading: true })
        try {
          const data = await activityService.fetchTimeline()
          set({ timelineData: data, loading: false })
        } catch (error) {
          set({ loading: false })
        }
      },

      // ... 其他操作
    }),
    {
      name: 'activity-store', // localStorage key
    }
  )
)
```

### 状态订阅最佳实践

```typescript
// ✅ 好：使用选择器精确订阅
const timelineData = useActivityStore((state) => state.timelineData)
const loading = useActivityStore((state) => state.loading)

// ❌ 差：订阅整个 store，会导致不必要的重新渲染
const store = useActivityStore()
```

### Agents Store

管理 Agent 任务。

```typescript
interface AgentsState {
  tasks: Task[]
  executingTaskId: string | null
  completedTaskCount: number

  fetchTasks: () => Promise<void>
  createTask: (task: Task) => Promise<void>
  updateTaskStatus: (taskId: string, status: TaskStatus) => Promise<void>
  executeTask: (taskId: string) => Promise<void>
}
```

### Settings Store

管理应用设置（LLM 配置、用户偏好等）。

```typescript
interface SettingsState {
  apiKey: string
  model: string
  language: 'en' | 'zh-CN'
  theme: 'light' | 'dark'

  updateApiKey: (key: string) => Promise<void>
  updateLanguage: (lang: string) => void
  updateTheme: (theme: string) => void
}
```

### UI Store

管理 UI 状态（侧边栏展开状态、选中菜单项等）。

```typescript
interface UIState {
  sidebarOpen: boolean
  selectedMenuItem: string

  toggleSidebar: () => void
  setSelectedMenuItem: (item: string) => void
}
```

## 数据同步

### 实时更新机制

iDO 使用 **Tauri 事件系统** 实现前后端实时同步。

```typescript
// 监听后端事件
import { listen } from '@tauri-apps/api/event'

useEffect(() => {
  const unlisten = listen('activity-created', (event) => {
    const newActivity = event.payload as Activity
    // 更新本地状态
    updateTimelineWithNewActivity(newActivity)
  })

  return () => unlisten.then((fn) => fn())
}, [])
```

### 活动增量更新

为了提高效率，前端使用**版本号**追踪数据更新。

```typescript
// 首次加载：获取完整数据
async function fetchActivityTimeline() {
  const data = await apiClient.getActivityTimeline()
  set({
    timelineData: data,
    currentMaxVersion: Math.max(...data.map((a) => a.version)),
  })
}

// 增量更新：只获取新数据
async function fetchActivitiesIncremental() {
  const newActivities = await apiClient.getActivitiesIncremental({
    sinceVersion: get().currentMaxVersion,
  })

  // 合并新数据到时间线
  const updated = [
    ...newActivities, // 新项在前
    ...get().timelineData,
  ]

  set({
    timelineData: updated,
    currentMaxVersion: Math.max(...updated.map((a) => a.version)),
  })
}
```

### 事件防抖

为了避免频繁更新，前端对活动更新和删除进行防抖处理。

```typescript
import { useRef } from 'react'

export function useActivityIncremental() {
  const debounceTimerRef = useRef<NodeJS.Timeout>()

  const handleActivityCreated = (activity: Activity) => {
    clearTimeout(debounceTimerRef.current)
    debounceTimerRef.current = setTimeout(() => {
      fetchActivitiesIncremental() // 300ms 后才获取增量更新
    }, 300)
  }

  useEffect(() => {
    const unlisten = listen('activity-created', (event) => {
      handleActivityCreated(event.payload)
    })

    return () => {
      clearTimeout(debounceTimerRef.current)
      unlisten.then((fn) => fn())
    }
  }, [])
}
```

## 路由和菜单

### 菜单配置驱动

菜单配置文件驱动整个应用的路由和导航菜单。

```typescript
// src/lib/config/menu.ts
export const menuConfig: MenuItem[] = [
  {
    id: 'activity',
    label: 'sidebar.activity',        // i18n key
    icon: 'Clock',
    path: '/activity',
    position: 'main',
  },
  {
    id: 'dashboard',
    label: 'sidebar.dashboard',
    icon: 'BarChart3',
    path: '/dashboard',
    position: 'main',
  },
  {
    id: 'agents',
    label: 'sidebar.agents',
    icon: 'Zap',
    path: '/agents',
    position: 'main',
    badge: { count: 3, type: 'info' }, // 展示任务数量
  },
  {
    id: 'settings',
    label: 'sidebar.settings',
    icon: 'Settings',
    path: '/settings',
    position: 'bottom',
  },
]
```

### 路由配置

```typescript
// src/routes/Index.tsx
import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'

const ActivityView = lazy(() => import('@/views/Activity'))
const DashboardView = lazy(() => import('@/views/Dashboard'))
const AgentsView = lazy(() => import('@/views/Agents'))
const SettingsView = lazy(() => import('@/views/Settings'))

export function AppRoutes() {
  return (
    <BrowserRouter>
      <Routes>
        <Route
          path="/activity"
          element={
            <Suspense fallback={<LoadingSpinner />}>
              <ActivityView />
            </Suspense>
          }
        />
        <Route path="/dashboard" element={<DashboardView />} />
        <Route path="/agents" element={<AgentsView />} />
        <Route path="/settings" element={<SettingsView />} />
      </Routes>
    </BrowserRouter>
  )
}
```

### 菜单组件

```typescript
// src/components/Common/Sidebar.tsx
import { menuConfig } from '@/lib/config/menu'
import { useUIStore } from '@/lib/stores'
import { useTranslation } from '@/hooks/useTranslation'

export function Sidebar() {
  const { t } = useTranslation()
  const selectedMenuItem = useUIStore((state) => state.selectedMenuItem)
  const setSelectedMenuItem = useUIStore((state) => state.setSelectedMenuItem)

  return (
    <nav>
      {menuConfig.map((item) => (
        <a
          key={item.id}
          href={item.path}
          className={selectedMenuItem === item.id ? 'active' : ''}
          onClick={() => setSelectedMenuItem(item.id)}
        >
          {t(item.label)}
          {item.badge && <Badge count={item.badge.count} />}
        </a>
      ))}
    </nav>
  )
}
```

## 最佳实践

### ✅ 状态管理

1. **选择性订阅**
   ```typescript
   // ✅ 好
   const data = useStore((state) => state.data)

   // ❌ 差
   const store = useStore()
   ```

2. **避免过度渲染**
   ```typescript
   // ✅ 使用 React.memo
   const Item = memo(({ data }) => <div>{data}</div>)

   // ✅ 使用 useMemo 缓存计算结果
   const filteredData = useMemo(() => {
     return data.filter(...)
   }, [data])
   ```

3. **事件处理优化**
   ```typescript
   // ✅ 使用 useCallback
   const handleClick = useCallback((id) => {
     updateItem(id)
   }, [updateItem])
   ```

### ✅ 数据流

1. **单向数据流**
   - 用户操作 → 事件处理 → Store 更新 → 组件重新渲染

2. **异步操作**
   ```typescript
   const fetchData = useStore((state) => state.fetchData)

   useEffect(() => {
     fetchData() // 在 mount 时调用
   }, [fetchData])
   ```

3. **错误处理**
   ```typescript
   try {
     await store.fetchData()
   } catch (error) {
     toast.error(t('errors.loadFailed'))
   }
   ```

### ✅ 类型安全

1. **定义完整的类型**
   ```typescript
   interface Activity {
     id: string
     name: string
     description: string
     timestamp: number
   }
   ```

2. **使用 Zod 验证**
   ```typescript
   import { z } from 'zod'

   const ActivitySchema = z.object({
     id: z.string(),
     name: z.string(),
   })

   const validated = ActivitySchema.parse(data)
   ```

### ✅ 性能优化

1. **图片优化**
   - 使用 WebP 格式
   - 实现图片懒加载
   - 压缩截图大小

2. **代码分割**
   ```typescript
   const View = lazy(() => import('./View'))
   ```

3. **虚拟滚动**
   - 使用 `react-window` 或自定义实现
   - 仅渲染可见项

### ✅ 国际化

```typescript
import { useTranslation } from '@/hooks/useTranslation'

function Component() {
  const { t } = useTranslation()
  return <h1>{t('activity.title')}</h1>
}
```

## 调试和开发工具

### React DevTools

```bash
# 在浏览器中安装 React DevTools 扩展
# 可以检查组件树、Props、Hooks 等
```

### Zustand DevTools

在 store 中添加 devtools 中间件：

```typescript
import { devtools } from 'zustand/middleware'

export const useActivityStore = create<ActivityState>(
  devtools(
    (set) => ({
      // ...
    }),
    { name: 'ActivityStore' }
  )
)
```

### TypeScript 编译检查

```bash
pnpm tsc --noEmit
```

## 获取帮助

- 📖 查看 [国际化文档](./i18n.md)
- 📖 查看 [开发指南](./development.md)
- 🐛 报告 Bug：[GitHub Issues](https://github.com/TexasOct/iDO/issues)
