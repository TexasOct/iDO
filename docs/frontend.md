# Rewind 前端设计文档

## 一、项目概述

Rewind 是一个基于 Tauri 的桌面应用，主要功能是记录和回溯用户的活动数据，并通过 AI Agent 助手帮助用户分析和处理这些数据。

### 核心功能

1. **活动记录**：以时间轴形式展示用户的活动数据，支持多层级数据结构（时间 → 活动 → 事件总结 → 事件 → 原始记录）
2. **统计面板**：可视化展示 LLM API tokens 使用量和 Agents 任务完成情况
3. **Agents 助手**：提供 AI Agent 任务的创建、执行、监控和管理功能
4. **系统设置**：配置 LLM 相关参数（BaseURL、API Key、Model）

## 二、技术栈

### 核心框架

- **Tauri 2.x**：跨平台桌面应用框架
- **React 19.x**：前端 UI 框架
- **Vite 6.x**：构建工具
- **TypeScript 5.x**：类型安全

### 状态管理

- **Zustand 5.x**：轻量级状态管理库

### UI 组件库

- **shadcn/ui**：基于 Radix UI 的组件库
- **Tailwind CSS 4.x**：原子化 CSS 框架
- **Lucide React**：图标库

### 路由

- **React Router 7.x**：客户端路由管理

### 后端通信

- **PyTauri**：Python 后端通信桥接（自动生成 client 代码）
- **Tauri Plugin HTTP**：HTTP 请求插件

### 其他工具

- **React Hook Form + Zod**：表单管理和验证
- **date-fns**：日期处理
- **Sonner**：Toast 通知
- **Vaul**：Drawer 组件

## 三、项目结构设计

```
src/
├── assets/                 # 静态资源
│   └── images/            # 图片资源
│
├── client/                # PyTauri 自动生成的 API 客户端（不要手动修改）
│   ├── apiClient.ts
│   └── _apiTypes.d.ts
│
├── components/            # 组件目录
│   ├── shadcn-ui/         # shadcn/ui 组件
│   ├── activity/          # 活动记录相关组件
│   ├── dashboard/         # 统计面板相关组件
│   ├── agents/            # Agents 助手相关组件
│   └── settings/          # 设置相关组件
│
├── hooks/               # 自定义 Hooks
│   ├── use-mobile.ts    # 移动端检测
│   └── use-*.ts         # 其他业务 Hooks
│
├── layouts/              # 布局组件
│   ├── MainLayout.tsx   # 主布局（左侧菜单 + 右侧内容）
│   └── SettingsLayout.tsx
│
├── lib/                  # 工具库
│   ├── stores/          # Zustand 状态管理
│   │   ├── activity.ts  # 活动记录状态
│   │   ├── agents.ts    # Agents 状态
│   │   ├── settings.ts  # 设置状态
│   │   └── ui.ts        # UI 状态（侧边栏选中等）
│   ├── services/        # 业务服务层
│   │   ├── activity/    # 活动记录服务
│   │   ├── agents/      # Agents 服务
│   │   ├── llm/         # LLM 服务
│   │   └── tauriFetch.ts
│   ├── types/           # 类型定义
│   │   ├── activity.ts
│   │   ├── agents.ts
│   │   └── settings.ts
│   └── utils.ts         # 工具函数
│
├── routes/              # 路由配置
│   └── Index.tsx
│
├── styles/              # 样式文件
│   └── index.css
│
├── types/               # 全局类型定义
│   ├── vite-env.d.ts
│   └── auto-imports.d.ts
│
├── views/               # 页面视图
│   ├── Activity/        # 活动记录页面
│   ├── Dashboard/       # 统计面板页面
│   ├── Agents/          # Agents 助手页面
│   ├── Settings/        # 设置页面
│   └── App.tsx          # 应用根组件
│
└── main.tsx            # 应用入口
```

## 四、核心功能模块设计

### 4.1 活动记录模块

#### 数据结构

```typescript
// lib/types/activity.ts
export interface RawRecord {
  id: string
  timestamp: number
  content: string
  metadata?: Record<string, any>
}

export interface Event {
  id: string
  type: string
  timestamp: number
  records: RawRecord[]
  summary?: string
}

export interface EventSummary {
  id: string
  title: string
  timestamp: number
  events: Event[]
}

export interface Activity {
  id: string
  name: string
  timestamp: number
  eventSummaries: EventSummary[]
}

export interface TimelineDay {
  date: string // YYYY-MM-DD
  activities: Activity[]
}
```

#### 状态管理

```typescript
// lib/stores/activity.ts
interface ActivityState {
  timelineData: TimelineDay[]
  selectedDate: string | null
  expandedItems: Set<string> // 记录展开的节点 ID

  // Actions
  fetchTimelineData: (dateRange: { start: string; end: string }) => Promise<void>
  setSelectedDate: (date: string) => void
  toggleExpanded: (id: string) => void
  expandAll: () => void
  collapseAll: () => void
}
```

#### 组件设计

- `ActivityTimeline`：时间轴容器组件
- `TimelineDay`：按日期分组的时间轴项
- `ActivityItem`：活动项组件（可折叠）
- `EventSummaryItem`：事件总结组件
- `EventItem`：事件组件
- `RecordItem`：原始记录组件

### 4.2 统计面板模块

#### 数据结构

```typescript
// lib/types/dashboard.ts
export interface TokenUsageData {
  timestamp: number
  tokens: number
  model?: string
}

export interface AgentTaskData {
  timestamp: number
  completed: number
  failed: number
  total: number
}

export interface DashboardMetrics {
  tokenUsage: TokenUsageData[]
  agentTasks: AgentTaskData[]
  period: 'day' | 'week' | 'month'
}
```

#### 状态管理

```typescript
// lib/stores/dashboard.ts
interface DashboardState {
  metrics: DashboardMetrics
  period: 'day' | 'week' | 'month'

  // Actions
  fetchMetrics: (period: 'day' | 'week' | 'month') => Promise<void>
  setPeriod: (period: 'day' | 'week' | 'month') => void
}
```

#### 组件设计

- `DashboardView`：统计面板容器
- `MetricsCard`：指标卡片组件
- `TokenUsageChart`：Token 使用量图表
- `AgentTaskChart`：Agent 任务完成量图表
- `PeriodSelector`：时间周期选择器

### 4.3 Agents 助手模块

#### 数据结构

```typescript
// lib/types/agents.ts
export type AgentType = 'WritingAgent' | 'ResearchAgent' | 'AnalysisAgent' | string

export type TaskStatus = 'todo' | 'processing' | 'done' | 'failed'

export interface AgentTask {
  id: string
  agent: AgentType
  planDescription: string
  status: TaskStatus
  createdAt: number
  startedAt?: number
  completedAt?: number
  duration?: number // 运行时长（秒）
  result?: {
    type: 'text' | 'file'
    content: string
    filePath?: string
  }
  error?: string
}

export interface AgentConfig {
  name: AgentType
  description: string
  icon?: string
}
```

#### 状态管理

```typescript
// lib/stores/agents.ts
interface AgentsState {
  tasks: AgentTask[]
  availableAgents: AgentConfig[]
  selectedAgent: AgentType | null
  planDescription: string

  // Actions
  fetchTasks: () => Promise<void>
  fetchAvailableAgents: () => Promise<void>
  createTask: (agent: AgentType, plan: string) => Promise<void>
  executeTask: (taskId: string) => Promise<void>
  stopTask: (taskId: string) => Promise<void>
  deleteTask: (taskId: string) => Promise<void>
  setSelectedAgent: (agent: AgentType | null) => void
  setPlanDescription: (description: string) => void
}
```

#### 组件设计

**Agents 视图主组件**

- `AgentsView`：Agents 助手容器组件
- `AgentSelector`：Agent 选择器（Dropdown 或 Select）
- `PlanInput`：计划描述输入框（Textarea）
- `TaskActions`：任务操作按钮组（执行、确认、删除）

**任务列表组件**

- `TaskList`：任务列表容器，包含三个标签页
  - `TodoTasks`：待办任务列表
  - `ProcessingTasks`：进行中任务列表
  - `DoneTasks`：已完成任务列表
- `TaskCard`：任务卡片组件，根据状态显示不同内容
  - Todo：显示基本信息 + 执行按钮
  - Processing：显示进度信息 + 停止按钮
  - Done：显示结果 + 删除按钮

**任务详情组件**

- `TaskDetail`：任务详情弹窗
- `TaskResultViewer`：结果查看器
  - 文本结果：使用 `Textarea` 或 `Card` 展示
  - 文件结果：提供下载/打开按钮

### 4.4 设置模块

#### 数据结构

```typescript
// lib/types/settings.ts
export interface LLMSettings {
  baseUrl: string
  apiKey: string
  model: string
}

export interface AppSettings {
  llm: LLMSettings
  theme: 'light' | 'dark' | 'system'
  language: 'zh-CN' | 'en-US'
}
```

#### 状态管理

```typescript
// lib/stores/settings.ts
interface SettingsState {
  settings: AppSettings

  // Actions
  fetchSettings: () => Promise<void>
  updateLLMSettings: (llm: Partial<LLMSettings>) => Promise<void>
  updateTheme: (theme: 'light' | 'dark' | 'system') => void
  updateLanguage: (language: 'zh-CN' | 'en-US') => void
}
```

#### 组件设计

- `SettingsView`：设置页面容器
- `LLMSettingsForm`：LLM 设置表单
- `ThemeToggle`：主题切换器（已存在）
- `LanguageSelector`：语言选择器

### 4.5 UI 状态管理

```typescript
// lib/stores/ui.ts
interface UIState {
  // 当前选中的菜单项
  activeMenuItem: 'activity' | 'dashboard' | 'agents' | 'settings'

  // 侧边栏是否折叠
  sidebarCollapsed: boolean

  // Actions
  setActiveMenuItem: (item: UIState['activeMenuItem']) => void
  toggleSidebar: () => void
}
```

## 五、布局设计

### 5.1 主布局（MainLayout）

#### 设计理念

采用配置驱动的菜单渲染方案，通过配置文件定义菜单项，便于扩展和维护。支持两种页面切换方案：

1. **Router 方案**（推荐）：基于 React Router 的声明式路由，支持浏览器前进/后退
2. **UI State 方案**：基于状态管理的条件渲染，适合简单应用

本项目采用 **Router 方案** + **UI State 同步** 的混合模式，确保菜单高亮与路由状态同步。

#### 菜单配置文件

```typescript
// lib/config/menu.ts
import { LucideIcon, Clock, BarChart, Bot, Settings } from 'lucide-react'

export interface MenuItem {
  id: string
  label: string
  icon: LucideIcon
  path: string
  position?: 'main' | 'bottom' // 菜单位置
  badge?: number // 角标数字（可选）
  hidden?: boolean // 是否隐藏
}

export const MENU_ITEMS: MenuItem[] = [
  {
    id: 'activity',
    label: '活动记录',
    icon: Clock,
    path: '/activity',
    position: 'main'
  },
  {
    id: 'dashboard',
    label: '统计面板',
    icon: BarChart,
    path: '/dashboard',
    position: 'main'
  },
  {
    id: 'agents',
    label: 'Agents 助手',
    icon: Bot,
    path: '/agents',
    position: 'main'
  },
  {
    id: 'settings',
    label: '设置',
    icon: Settings,
    path: '/settings',
    position: 'bottom'
  }
]

// 根据位置分组菜单项
export const getMenuItemsByPosition = (position: 'main' | 'bottom') => {
  return MENU_ITEMS.filter(item => !item.hidden && item.position === position)
}
```

#### UI 状态管理（增强版）

```typescript
// lib/stores/ui.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type MenuItemId = 'activity' | 'dashboard' | 'agents' | 'settings'

interface UIState {
  // 当前激活的菜单项（与路由同步）
  activeMenuItem: MenuItemId

  // 侧边栏是否折叠
  sidebarCollapsed: boolean

  // 通知角标数据
  badges: Record<string, number>

  // Actions
  setActiveMenuItem: (item: MenuItemId) => void
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
  setBadge: (menuId: string, count: number) => void
  clearBadge: (menuId: string) => void
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      activeMenuItem: 'activity',
      sidebarCollapsed: false,
      badges: {},

      setActiveMenuItem: (item) => set({ activeMenuItem: item }),
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      setBadge: (menuId, count) =>
        set((state) => ({
          badges: { ...state.badges, [menuId]: count }
        })),
      clearBadge: (menuId) =>
        set((state) => {
          const { [menuId]: _, ...rest } = state.badges
          return { badges: rest }
        })
    }),
    {
      name: 'rewind-ui-state',
      // 只持久化部分状态
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed
      })
    }
  )
)
```

#### 主布局组件实现

```typescript
// layouts/MainLayout.tsx
import { useEffect } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router'
import { cn } from '@/lib/utils'
import { useUIStore } from '@/lib/stores/ui'
import { MENU_ITEMS, getMenuItemsByPosition } from '@/lib/config/menu'
import { MenuButton } from '@/components/shared/MenuButton'
import { Sidebar } from '@/components/layout/Sidebar'

export function MainLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { activeMenuItem, setActiveMenuItem, sidebarCollapsed } = useUIStore()

  // 路由变化时同步 UI 状态
  useEffect(() => {
    const currentPath = location.pathname
    const matchedItem = MENU_ITEMS.find(item => item.path === currentPath)
    if (matchedItem && matchedItem.id !== activeMenuItem) {
      setActiveMenuItem(matchedItem.id as any)
    }
  }, [location.pathname, activeMenuItem, setActiveMenuItem])

  // 菜单点击处理
  const handleMenuClick = (menuId: string, path: string) => {
    setActiveMenuItem(menuId as any)
    navigate(path)
  }

  const mainMenuItems = getMenuItemsByPosition('main')
  const bottomMenuItems = getMenuItemsByPosition('bottom')

  return (
    <div className="flex h-screen w-screen overflow-hidden">
      {/* 左侧菜单栏 */}
      <Sidebar
        collapsed={sidebarCollapsed}
        mainItems={mainMenuItems}
        bottomItems={bottomMenuItems}
        activeItemId={activeMenuItem}
        onMenuClick={handleMenuClick}
      />

      {/* 右侧内容区域 */}
      <main className="flex-1 overflow-hidden bg-background">
        <Outlet />
      </main>
    </div>
  )
}
```

### 5.2 侧边栏组件

```typescript
// components/layout/Sidebar.tsx
import { cn } from '@/lib/utils'
import { MenuItem } from '@/lib/config/menu'
import { MenuButton } from '@/components/shared/MenuButton'
import { useUIStore } from '@/lib/stores/ui'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface SidebarProps {
  collapsed: boolean
  mainItems: MenuItem[]
  bottomItems: MenuItem[]
  activeItemId: string
  onMenuClick: (menuId: string, path: string) => void
}

export function Sidebar({
  collapsed,
  mainItems,
  bottomItems,
  activeItemId,
  onMenuClick
}: SidebarProps) {
  const { toggleSidebar, badges } = useUIStore()

  return (
    <aside
      className={cn(
        'flex flex-col border-r bg-card transition-all duration-200',
        collapsed ? 'w-16' : 'w-64'
      )}
    >
      {/* Logo 区域 */}
      <div className="flex h-14 items-center border-b px-4">
        {!collapsed && (
          <h1 className="text-lg font-semibold">Rewind</h1>
        )}
      </div>

      {/* 主菜单区域 */}
      <div className="flex-1 space-y-1 overflow-y-auto p-2">
        {mainItems.map((item) => (
          <MenuButton
            key={item.id}
            icon={item.icon}
            label={item.label}
            active={activeItemId === item.id}
            collapsed={collapsed}
            badge={badges[item.id]}
            onClick={() => onMenuClick(item.id, item.path)}
          />
        ))}
      </div>

      {/* 底部菜单区域 */}
      <div className="space-y-1 border-t p-2">
        {bottomItems.map((item) => (
          <MenuButton
            key={item.id}
            icon={item.icon}
            label={item.label}
            active={activeItemId === item.id}
            collapsed={collapsed}
            badge={badges[item.id]}
            onClick={() => onMenuClick(item.id, item.path)}
          />
        ))}

        {/* 折叠/展开按钮 */}
        <Button
          variant="ghost"
          size="sm"
          onClick={toggleSidebar}
          className="w-full justify-start"
        >
          {collapsed ? (
            <ChevronRight className="h-5 w-5" />
          ) : (
            <>
              <ChevronLeft className="h-5 w-5" />
              <span className="ml-2">收起</span>
            </>
          )}
        </Button>
      </div>
    </aside>
  )
}
```

### 5.3 菜单按钮组件（增强版）

```typescript
// components/shared/MenuButton.tsx
import { cn } from '@/lib/utils'
import { LucideIcon } from 'lucide-react'
import { Badge } from '@/components/ui/badge'

interface MenuButtonProps {
  icon: LucideIcon
  label: string
  active?: boolean
  collapsed?: boolean
  badge?: number
  onClick?: () => void
}

export function MenuButton({
  icon: Icon,
  label,
  active,
  collapsed,
  badge,
  onClick
}: MenuButtonProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'relative flex w-full items-center gap-3 rounded-lg px-3 py-2.5 transition-all',
        'hover:bg-accent hover:text-accent-foreground',
        active && 'bg-accent text-accent-foreground font-medium',
        collapsed && 'justify-center'
      )}
      title={collapsed ? label : undefined}
    >
      <Icon className="h-5 w-5 flex-shrink-0" />

      {!collapsed && (
        <span className="flex-1 truncate text-left">{label}</span>
      )}

      {/* 角标 */}
      {badge !== undefined && badge > 0 && (
        <Badge
          variant="destructive"
          className={cn(
            'h-5 min-w-[20px] px-1 text-xs',
            collapsed && 'absolute -right-1 -top-1'
          )}
        >
          {badge > 99 ? '99+' : badge}
        </Badge>
      )}
    </button>
  )
}
```

### 5.4 页面切换方案对比

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **React Router** | 支持浏览器历史、URL 管理、懒加载、代码分割 | 配置稍复杂 | 中大型应用、需要 URL 管理 |
| **UI State 条件渲染** | 简单直观、无需路由配置 | 无浏览器历史、组件始终挂载、无法深度链接 | 简单应用、嵌入式场景 |

**本项目采用 React Router 方案的理由**：

1. 支持浏览器前进/后退，用户体验更好
2. 支持路由懒加载，减少初始加载时间
3. 便于未来扩展（如任务详情页、设置子页面）
4. 支持通过 URL 直接访问特定页面

## 六、组件划分与职责

### 6.1 组件分层架构

采用分层组件架构，将组件划分为四个层级：

```
┌─────────────────────────────────────┐
│   Pages (视图层)                     │  业务逻辑、数据获取、状态管理
├─────────────────────────────────────┤
│   Containers (容器组件)              │  组合多个组件、处理复杂交互
├─────────────────────────────────────┤
│   Components (展示组件)              │  纯 UI 展示、接收 props
├─────────────────────────────────────┤
│   Primitives (基础组件 shadcn/ui)   │  原子级 UI 组件
└─────────────────────────────────────┘
```

### 6.2 核心组件职责划分

#### 活动记录模块组件树

```
ActivityView (Page)
├── ActivityHeader (Container)
│   ├── DateRangePicker
│   └── SearchInput
├── ActivityTimeline (Container)
│   ├── TimelineDay
│   │   └── ActivityItem
│   │       └── EventSummaryItem
│   │           └── EventItem
│   │               └── RecordItem (Component)
│   └── VirtualList (性能优化)
└── ActivityFilters (Container)
    ├── FilterButton
    └── FilterDialog
```

**组件职责**：

- **ActivityView**：页面容器，负责数据获取、状态管理、组件编排
- **ActivityHeader**：顶部操作栏，处理日期选择和搜索
- **ActivityTimeline**：时间轴容器，管理展开/折叠状态
- **TimelineDay/ActivityItem/EventSummaryItem/EventItem/RecordItem**：纯展示组件，接收数据 props

#### Agents 模块组件树

```
AgentsView (Page)
├── AgentCreator (Container)
│   ├── AgentSelector (Component)
│   ├── PlanInput (Component)
│   └── ActionButtons (Component)
├── TaskTabs (Container)
│   ├── TodoTaskList
│   │   └── TaskCard
│   ├── ProcessingTaskList
│   │   └── TaskCard (Processing 变体)
│   └── DoneTaskList
│       └── TaskCard (Done 变体)
└── TaskDetailDialog (Container)
    ├── TaskInfo
    ├── TaskProgress (仅 Processing)
    └── TaskResult (仅 Done)
```

**组件职责**：

- **AgentsView**：页面容器，管理任务列表状态
- **AgentCreator**：任务创建区，处理表单提交
- **TaskTabs**：任务列表标签页，按状态分类展示
- **TaskCard**：任务卡片，根据状态显示不同内容（多态组件）
- **TaskDetailDialog**：任务详情弹窗，展示完整信息

#### 统计面板模块组件树

```
DashboardView (Page)
├── DashboardHeader (Container)
│   └── PeriodSelector (Component)
├── MetricsGrid (Container)
│   ├── MetricCard (Token 使用量)
│   ├── MetricCard (任务完成数)
│   └── MetricCard (成功率)
└── ChartsSection (Container)
    ├── TokenUsageChart (Component)
    └── AgentTaskChart (Component)
```

### 6.3 组件复用策略

#### 1. 通用卡片组件

```typescript
// components/shared/Card.tsx
interface CardProps {
  title: string
  description?: string
  icon?: LucideIcon
  value?: string | number
  trend?: { value: number; isPositive: boolean }
  children?: React.ReactNode
}

export function Card({ title, description, icon: Icon, value, trend, children }: CardProps) {
  // 可复用的卡片组件，支持多种展示模式
}
```

#### 2. 空状态组件

```typescript
// components/shared/EmptyState.tsx
interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description?: string
  action?: { label: string; onClick: () => void }
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  // 统一的空状态展示
}
```

#### 3. 加载骨架屏

```typescript
// components/shared/Skeleton.tsx
export const ActivitySkeleton = () => { /* ... */ }
export const TaskCardSkeleton = () => { /* ... */ }
export const ChartSkeleton = () => { /* ... */ }
```

## 七、跨组件通信方案

### 7.1 通信模式分类

| 场景 | 通信方式 | 示例 |
|------|----------|------|
| **父子组件** | Props / Callbacks | ActivityTimeline → ActivityItem |
| **兄弟组件** | 状态提升 / Context | SearchInput ↔ ActivityTimeline |
| **跨层级组件** | Zustand Store | 任意组件访问 Agent 任务列表 |
| **全局事件** | Tauri Events | 后端推送任务状态更新 |

### 7.2 通信实现方案

#### 方案 1：Props Drilling（适用于 1-2 层嵌套）

```typescript
// 适用场景：父子组件、浅层嵌套
<ActivityTimeline>
  <ActivityItem
    data={activity}
    expanded={expandedItems.has(activity.id)}
    onToggle={() => toggleExpanded(activity.id)}
  />
</ActivityTimeline>
```

#### 方案 2：Zustand Store（适用于跨层级、多组件共享）

```typescript
// 适用场景：多个组件需要访问/修改同一状态
// lib/stores/agents.ts
export const useAgentsStore = create<AgentsState>((set, get) => ({
  tasks: [],

  createTask: async (agent, plan) => {
    const newTask = await apiClient.createTask({ agent, plan })
    set((state) => ({ tasks: [...state.tasks, newTask] }))
  },

  updateTaskStatus: (taskId, status) => {
    set((state) => ({
      tasks: state.tasks.map(task =>
        task.id === taskId ? { ...task, status } : task
      )
    }))
  }
}))

// 在任意组件中使用
const tasks = useAgentsStore(state => state.tasks)
const createTask = useAgentsStore(state => state.createTask)
```

#### 方案 3：Context（适用于主题、配置等全局数据）

```typescript
// 适用场景：主题、语言、配置等全局数据
// lib/contexts/ThemeContext.tsx
export const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState<'light' | 'dark'>('light')

  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

// 使用
const { theme, setTheme } = useTheme()
```

#### 方案 4：Tauri Events（适用于后端→前端实时推送）

```typescript
// 适用场景：后端主动推送数据更新
// hooks/useTaskUpdates.ts
export function useTaskUpdates() {
  const updateTaskStatus = useAgentsStore(state => state.updateTaskStatus)

  useEffect(() => {
    const unlisten = listen<TaskUpdatePayload>('agent-task-update', (event) => {
      const { taskId, status, progress } = event.payload
      updateTaskStatus(taskId, { status, progress })
    })

    return () => {
      unlisten.then(fn => fn())
    }
  }, [updateTaskStatus])
}

// 在 AgentsView 中使用
export function AgentsView() {
  useTaskUpdates() // 自动监听后端推送
  // ...
}
```

### 7.3 数据流向示意图

```
┌──────────────────────────────────────────────────┐
│                   User Action                     │
└─────────────────┬────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│              Component Event Handler              │
│  (onClick, onChange, onSubmit...)                │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│             Zustand Store Action                 │
│  (createTask, fetchTimeline, updateSettings...)  │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│              Service Layer                       │
│  (API calls via PyTauri Client)                  │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│              Backend (Rust/Python)               │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│          Response / Tauri Event                  │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│            Update Zustand Store                  │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────┐
│          Components Re-render                    │
└──────────────────────────────────────────────────┘
```

### 7.4 最佳实践

#### 1. 避免 Props Drilling

```typescript
// ❌ 不好：层层传递 props
<Page>
  <Container onAction={handleAction}>
    <SubContainer onAction={handleAction}>
      <Component onAction={handleAction} />
    </SubContainer>
  </Container>
</Page>

// ✅ 好：使用 Store
// 在需要的组件中直接访问
const handleAction = useAgentsStore(state => state.createTask)
```

#### 2. 精细化订阅

```typescript
// ❌ 不好：订阅整个 store（任何变化都会触发重渲染）
const store = useAgentsStore()

// ✅ 好：只订阅需要的字段
const tasks = useAgentsStore(state => state.tasks)
const createTask = useAgentsStore(state => state.createTask)
```

#### 3. 职责分离

```typescript
// ✅ 好：数据逻辑在 Store，展示逻辑在 Component
// Store
export const useAgentsStore = create((set) => ({
  tasks: [],
  getTodoTasks: () => get().tasks.filter(t => t.status === 'todo')
}))

// Component
export function TodoTaskList() {
  const todoTasks = useAgentsStore(state => state.getTodoTasks())
  return <TaskList tasks={todoTasks} />
}
```

## 八、路由设计

### 8.1 路由配置（支持懒加载）

```typescript
// routes/Index.tsx
import { createBrowserRouter } from 'react-router'
import { lazy, Suspense } from 'react'
import { App } from '@/views/App'
import { MainLayout } from '@/layouts/MainLayout'
import { LoadingPage } from '@/components/shared/LoadingPage'

// 懒加载页面组件
const ActivityView = lazy(() => import('@/views/Activity'))
const DashboardView = lazy(() => import('@/views/Dashboard'))
const AgentsView = lazy(() => import('@/views/Agents'))
const SettingsView = lazy(() => import('@/views/Settings'))

// 路由配置（自动生成自菜单配置）
import { MENU_ITEMS } from '@/lib/config/menu'

export const router = createBrowserRouter([
  {
    path: '/',
    Component: App,
    errorElement: <ErrorPage />,
    children: [
      {
        path: '/',
        Component: MainLayout,
        children: [
          // 默认路由重定向到第一个菜单项
          {
            index: true,
            loader: () => redirect(MENU_ITEMS[0].path)
          },
          {
            path: 'activity',
            element: (
              <Suspense fallback={<LoadingPage />}>
                <ActivityView />
              </Suspense>
            )
          },
          {
            path: 'dashboard',
            element: (
              <Suspense fallback={<LoadingPage />}>
                <DashboardView />
              </Suspense>
            )
          },
          {
            path: 'agents',
            element: (
              <Suspense fallback={<LoadingPage />}>
                <AgentsView />
              </Suspense>
            ),
            children: [
              // 嵌套路由示例：任务详情页
              {
                path: ':taskId',
                element: <TaskDetailPage />
              }
            ]
          },
          {
            path: 'settings',
            element: (
              <Suspense fallback={<LoadingPage />}>
                <SettingsView />
              </Suspense>
            ),
            children: [
              // 设置子页面
              { index: true, element: <GeneralSettings /> },
              { path: 'llm', element: <LLMSettings /> },
              { path: 'appearance', element: <AppearanceSettings /> }
            ]
          }
        ]
      }
    ]
  }
])
```

### 8.2 自动路由生成（可选方案）

```typescript
// lib/utils/routeGenerator.ts
import { MENU_ITEMS } from '@/lib/config/menu'
import { RouteObject } from 'react-router'

// 根据菜单配置自动生成路由
export function generateRoutesFromMenu(menuItems: MenuItem[]): RouteObject[] {
  return menuItems.map(item => ({
    path: item.path.replace(/^\//, ''), // 移除前导斜杠
    lazy: async () => {
      const module = await import(`@/views/${item.id.charAt(0).toUpperCase() + item.id.slice(1)}`)
      return { Component: module.default }
    }
  }))
}

// 使用
const routes = generateRoutesFromMenu(MENU_ITEMS)
```

## 九、项目文件结构细化

### 9.1 完整目录结构

```
src/
├── assets/                          # 静态资源
│   ├── images/                      # 图片资源
│   │   ├── logo.svg
│   │   └── empty-states/            # 空状态插图
│   └── fonts/                       # 字体文件（可选）
│
├── client/                          # PyTauri 自动生成（不要手动修改）
│   ├── apiClient.ts
│   └── _apiTypes.d.ts
│
├── components/                      # 组件目录
│   ├── ui/                          # shadcn/ui 基础组件
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── dialog.tsx
│   │   ├── input.tsx
│   │   ├── select.tsx
│   │   ├── tabs.tsx
│   │   └── ...
│   │
│   ├── layout/                      # 布局组件
│   │   ├── Sidebar.tsx              # 侧边栏
│   │   ├── Header.tsx               # 顶部栏（可选）
│   │   └── PageContainer.tsx        # 页面容器
│   │
│   ├── shared/                      # 通用业务组件
│   │   ├── MenuButton.tsx           # 菜单按钮
│   │   ├── EmptyState.tsx           # 空状态
│   │   ├── LoadingPage.tsx          # 加载页面
│   │   ├── ErrorBoundary.tsx        # 错误边界
│   │   └── Skeleton.tsx             # 骨架屏
│   │
│   ├── activity/                    # 活动记录模块组件
│   │   ├── ActivityHeader.tsx
│   │   ├── ActivityTimeline.tsx
│   │   ├── TimelineDay.tsx
│   │   ├── ActivityItem.tsx
│   │   ├── EventSummaryItem.tsx
│   │   ├── EventItem.tsx
│   │   ├── RecordItem.tsx
│   │   └── ActivityFilters.tsx
│   │
│   ├── dashboard/                   # 统计面板模块组件
│   │   ├── DashboardHeader.tsx
│   │   ├── MetricsGrid.tsx
│   │   ├── MetricCard.tsx
│   │   ├── TokenUsageChart.tsx
│   │   ├── AgentTaskChart.tsx
│   │   └── PeriodSelector.tsx
│   │
│   ├── agents/                      # Agents 模块组件
│   │   ├── AgentCreator.tsx
│   │   ├── AgentSelector.tsx
│   │   ├── PlanInput.tsx
│   │   ├── TaskTabs.tsx
│   │   ├── TaskCard.tsx
│   │   ├── TaskDetailDialog.tsx
│   │   ├── TaskProgress.tsx
│   │   └── TaskResult.tsx
│   │
│   └── settings/                    # 设置模块组件
│       ├── LLMSettingsForm.tsx
│       ├── ThemeToggle.tsx
│       └── LanguageSelector.tsx
│
├── hooks/                           # 自定义 Hooks
│   ├── use-mobile.ts                # shadcn/ui 提供
│   ├── use-task-updates.ts          # 监听任务更新
│   ├── use-debounce.ts              # 防抖
│   └── use-local-storage.ts         # 本地存储
│
├── layouts/                         # 布局组件
│   ├── MainLayout.tsx               # 主布局
│   └── AuthLayout.tsx               # 认证布局（可选）
│
├── lib/                             # 核心库
│   ├── config/                      # 配置文件
│   │   ├── menu.ts                  # 菜单配置
│   │   └── constants.ts             # 常量定义
│   │
│   ├── stores/                      # Zustand 状态管理
│   │   ├── activity.ts
│   │   ├── agents.ts
│   │   ├── dashboard.ts
│   │   ├── settings.ts
│   │   └── ui.ts
│   │
│   ├── services/                    # 业务服务层
│   │   ├── activity/
│   │   │   └── index.ts
│   │   ├── agents/
│   │   │   └── index.ts
│   │   ├── dashboard/
│   │   │   └── index.ts
│   │   ├── llm/
│   │   │   └── index.ts
│   │   └── tauriFetch.ts            # Tauri HTTP 封装
│   │
│   ├── types/                       # 类型定义
│   │   ├── activity.ts
│   │   ├── agents.ts
│   │   ├── dashboard.ts
│   │   ├── settings.ts
│   │   └── common.ts                # 通用类型
│   │
│   └── utils.ts                     # 工具函数（cn 等）
│
├── routes/                          # 路由配置
│   └── index.tsx
│
├── styles/                          # 样式文件
│   └── index.css                    # 全局样式 + Tailwind
│
├── types/                           # 全局类型声明
│   ├── vite-env.d.ts                # Vite 环境变量
│   └── auto-imports.d.ts            # 自动导入类型
│
├── views/                           # 页面视图
│   ├── Activity/
│   │   └── index.tsx                # 活动记录页面
│   ├── Dashboard/
│   │   └── index.tsx                # 统计面板页面
│   ├── Agents/
│   │   ├── index.tsx                # Agents 列表页面
│   │   └── TaskDetail.tsx           # 任务详情页面
│   ├── Settings/
│   │   ├── index.tsx                # 设置主页面
│   │   ├── General.tsx              # 通用设置
│   │   ├── LLM.tsx                  # LLM 设置
│   │   └── Appearance.tsx           # 外观设置
│   ├── App.tsx                      # 应用根组件
│   └── ErrorPage.tsx                # 错误页面
│
└── main.tsx                         # 应用入口
```

### 9.2 关键文件说明

#### 应用入口（main.tsx）

```typescript
// main.tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider } from 'react-router'
import { router } from '@/routes'
import '@/styles/index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
)
```

#### 应用根组件（views/App.tsx）

```typescript
// views/App.tsx
import { Outlet } from 'react-router'
import { Toaster } from '@/components/ui/sonner'
import { ErrorBoundary } from '@/components/shared/ErrorBoundary'

export function App() {
  return (
    <ErrorBoundary>
      <div className="h-screen w-screen overflow-hidden">
        <Outlet />
        <Toaster position="top-right" />
      </div>
    </ErrorBoundary>
  )
}
```

#### 页面示例（views/Activity/index.tsx）

```typescript
// views/Activity/index.tsx
import { useEffect } from 'react'
import { useActivityStore } from '@/lib/stores/activity'
import { ActivityHeader } from '@/components/activity/ActivityHeader'
import { ActivityTimeline } from '@/components/activity/ActivityTimeline'
import { ActivitySkeleton } from '@/components/shared/Skeleton'

export default function ActivityView() {
  const { timelineData, fetchTimelineData, loading } = useActivityStore()

  useEffect(() => {
    fetchTimelineData({
      start: '2025-10-01',
      end: '2025-10-18'
    })
  }, [fetchTimelineData])

  return (
    <div className="flex h-full flex-col">
      <ActivityHeader />
      <div className="flex-1 overflow-y-auto p-6">
        {loading ? (
          <ActivitySkeleton />
        ) : (
          <ActivityTimeline data={timelineData} />
        )}
      </div>
    </div>
  )
}
```

## 十、样式规范

### 10.1 设计系统

使用 shadcn/ui + Tailwind CSS 的设计系统，主要颜色变量：

```css
/* styles/index.css */
@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 0 0% 3.9%;
    --card: 0 0% 100%;
    --card-foreground: 0 0% 3.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 0 0% 3.9%;
    --primary: 0 0% 9%;
    --primary-foreground: 0 0% 98%;
    --secondary: 0 0% 96.1%;
    --secondary-foreground: 0 0% 9%;
    --muted: 0 0% 96.1%;
    --muted-foreground: 0 0% 45.1%;
    --accent: 0 0% 96.1%;
    --accent-foreground: 0 0% 9%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 0 0% 98%;
    --border: 0 0% 89.8%;
    --input: 0 0% 89.8%;
    --ring: 0 0% 3.9%;
    --radius: 0.5rem;
  }

  .dark {
    --background: 0 0% 3.9%;
    --foreground: 0 0% 98%;
    /* ... 其他暗色主题变量 */
  }
}
```

### 10.2 组件样式约定

1. **间距规范**

   - 容器内边距：`p-4` 或 `p-6`
   - 组件间距：`space-y-4` 或 `gap-4`
   - 卡片间距：`space-y-2`

2. **圆角规范**

   - 按钮/输入框：`rounded-lg`
   - 卡片：`rounded-xl`
   - 对话框：`rounded-2xl`

3. **阴影规范**

   - 卡片悬浮：`shadow-sm hover:shadow-md`
   - 模态框：`shadow-lg`

4. **过渡动画**
   - 通用过渡：`transition-colors`
   - 布局变化：`transition-all`
   - 时长：默认 150ms

## 十一、数据流设计

### 11.1 PyTauri 后端通信

```typescript
// lib/services/activity/index.ts
import { apiClient } from '@/client/apiClient'

export async function fetchActivityTimeline(dateRange: { start: string; end: string }) {
  try {
    // 调用 PyTauri 自动生成的 API 客户端
    const response = await apiClient.getActivityTimeline(dateRange)
    return response
  } catch (error) {
    console.error('Failed to fetch activity timeline:', error)
    throw error
  }
}
```

### 11.2 状态更新流程

1. 用户交互触发 Action
2. Action 调用 Service 层获取数据
3. Service 通过 PyTauri Client 与后端通信
4. 数据返回后更新 Zustand Store
5. 组件通过 Store 订阅自动重新渲染

```typescript
// 示例：获取活动记录
const { fetchTimelineData } = useActivityStore()

useEffect(() => {
  fetchTimelineData({
    start: '2025-10-01',
    end: '2025-10-18'
  })
}, [fetchTimelineData])
```

## 十二、开发规范

### 12.1 命名规范

- **组件**：PascalCase，如 `ActivityTimeline`
- **Hooks**：camelCase，以 `use` 开头，如 `useActivityStore`
- **工具函数**：camelCase，如 `formatDate`
- **类型/接口**：PascalCase，如 `Activity`、`AgentTask`
- **常量**：UPPER_SNAKE_CASE，如 `MAX_RETRY_COUNT`

### 12.2 文件组织规范

- 每个组件一个文件夹，包含 `index.tsx` 和相关的子组件
- 复杂组件拆分为多个子组件，放在同一文件夹下
- 类型定义优先放在 `lib/types/`，组件私有类型可以放在组件文件内

### 12.3 代码风格

- 使用 **Prettier** 进行代码格式化
- 使用 **TypeScript** 严格模式
- 组件使用**函数式组件** + **Hooks**
- 避免使用 `any`，优先使用具体类型或 `unknown`

### 12.4 性能优化

1. **使用 React.memo**：对于纯展示组件使用 memo 避免不必要的重渲染
2. **使用 useMemo/useCallback**：缓存计算结果和回调函数
3. **虚拟滚动**：活动记录列表较长时使用虚拟滚动（可考虑 `react-virtual`）
4. **懒加载**：路由组件使用 React.lazy 懒加载
5. **Store 订阅优化**：只订阅需要的状态字段

```typescript
// 好的做法：只订阅需要的字段
const tasks = useAgentsStore((state) => state.tasks)

// 避免：订阅整个 store
const agentsStore = useAgentsStore()
```

## 十三、关键交互流程

### 13.1 活动记录时间轴展开/折叠

1. 用户点击活动项
2. 调用 `toggleExpanded(id)`
3. Store 更新 `expandedItems` Set
4. 组件根据 ID 是否在 Set 中决定展开状态
5. 使用 CSS 过渡动画展示折叠效果

### 13.2 Agent 任务执行流程

1. 用户选择 Agent 类型
2. 输入计划描述
3. 点击"执行"按钮
4. 调用 `createTask()` 创建任务
5. 任务状态变为 `todo`
6. 调用 `executeTask(taskId)` 执行任务
7. 任务状态变为 `processing`
8. 后端定期推送进度更新（通过 WebSocket 或轮询）
9. 任务完成后状态变为 `done` 或 `failed`
10. 显示结果或错误信息

### 13.3 统计数据更新流程

1. 组件挂载时调用 `fetchMetrics(period)`
2. 用户切换时间周期时重新调用
3. 数据返回后使用图表库（如 Recharts 或 Chart.js）渲染
4. 支持数据实时更新（可选，通过定时器或 WebSocket）

## 十四、待实现功能清单

### 第一阶段（MVP）

- [ ] 主布局和菜单栏
- [ ] 活动记录时间轴基础展示
- [ ] Agents 助手任务列表（Todo/Processing/Done）
- [ ] 设置页面（LLM 配置）

### 第二阶段

- [ ] 统计面板图表展示
- [ ] 活动记录搜索和筛选
- [ ] Agent 任务详情弹窗
- [ ] 主题切换功能

### 第三阶段

- [ ] 实时数据更新
- [ ] 数据导出功能
- [ ] 键盘快捷键支持
- [ ] 多语言支持

## 十五、技术难点和解决方案

### 15.1 时间轴数据层级展示

**难点**：五层嵌套结构（时间 → 活动 → 事件总结 → 事件 → 记录）的展示和性能优化

**解决方案**：

- 使用递归组件渲染树形结构
- 使用 `expandedItems` Set 管理展开状态
- 虚拟滚动优化长列表性能
- 延迟加载子节点数据

### 15.2 Agent 任务实时状态更新

**难点**：Processing 状态的任务需要实时更新进度

**解决方案**：

- 方案 1：轮询（简单但消耗资源）
- 方案 2：Tauri Events（推荐，后端通过 emit 推送事件）
- 方案 3：WebSocket（适合高频更新）

```typescript
// 使用 Tauri Events 监听任务状态
import { listen } from '@tauri-apps/api/event'

useEffect(() => {
  const unlisten = listen('agent-task-update', (event) => {
    const taskUpdate = event.payload as { id: string; status: TaskStatus; progress?: number }
    updateTaskStatus(taskUpdate)
  })

  return () => {
    unlisten.then((fn) => fn())
  }
}, [])
```

### 15.3 大数据量统计图表性能

**难点**：Token 使用量和任务完成量可能有大量数据点

**解决方案**：

- 数据采样：后端返回聚合数据而非原始数据
- 图表懒加载：切换到统计面板时才加载
- 使用高性能图表库：如 Apache ECharts 或 Recharts
- 数据缓存：避免重复请求

## 十六、总结

本设计文档基于 Tauri + React + Vite 技术栈，采用模块化、组件化的设计思路，将 Rewind 应用划分为活动记录、统计面板、Agents 助手和设置四大核心模块。通过 Zustand 进行状态管理，shadcn/ui + Tailwind CSS 构建 UI，PyTauri 实现前后端通信。

### 核心设计原则

1. **模块化**：功能模块清晰分离，易于维护和扩展
2. **类型安全**：全面使用 TypeScript，避免运行时错误
3. **组件复用**：抽象通用组件，提高开发效率
4. **性能优化**：合理使用 memo、虚拟滚动等优化手段
5. **用户体验**：流畅的动画、实时反馈、清晰的视觉层级

### 下一步行动

1. 搭建项目基础结构（文件夹、路由、布局）
2. 实现主布局和菜单栏
3. 逐个实现各功能模块
4. 集成后端 API
5. 性能优化和测试
