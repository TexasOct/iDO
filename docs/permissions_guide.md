# macOS 权限引导系统

## 概述

Rewind 在 macOS 上需要两个关键权限才能正常运行：
1. **辅助功能权限** - 用于监听键盘和鼠标事件
2. **屏幕录制权限** - 用于截取屏幕快照

本文档详细说明了整个权限检测、引导和自动重启流程的实现。

## 架构设计

### 流程图

```
应用启动
    ↓
PermissionsGuide 组件挂载
    ↓
调用 checkPermissions API
    ↓
后端检查系统权限状态
    ↓
返回 PermissionsCheckResponse
    ↓
检查 allGranted 和 needsRestart 标志
    ↓
如果权限未全部授予：显示权限引导弹窗
    ↓
用户点击"打开设置"或"稍后"
    ↓
如果权限已授予：显示"已授予"状态 + 重启按钮
    ↓
用户点击"重启应用"
    ↓
调用 restartApp API
    ↓
后端延迟 1 秒后重启应用
```

## 后端实现

### 权限检查核心 (`backend/system/permissions.py`)

#### PermissionChecker 类

```python
class PermissionChecker:
    def check_all_permissions(self) -> PermissionsCheckResponse
    def _check_macos_accessibility(self) -> PermissionStatus
    def _check_macos_screen_recording(self) -> PermissionStatus
    def open_system_settings(self, permission_type: PermissionType) -> bool
    def request_accessibility_permission(self) -> bool
```

#### 权限检查方法

**1. 辅助功能权限检查**
- 使用 PyObjC Quartz 的 `AXIsProcessTrustedWithOptions`
- 检查应用是否在系统信任列表中
- 返回 `GRANTED`, `NOT_DETERMINED`, 或 `DENIED`

**2. 屏幕录制权限检查**
- 尝试截图并检查图像亮度
- 如果截图全黑，表示权限被拒绝
- 使用 numpy 计算平均亮度

### API 端点 (`backend/handlers/permissions.py`)

#### 1. 检查权限
```http
GET /api/permissions/check
```

**响应:**
```json
{
  "allGranted": false,
  "permissions": {
    "accessibility": {
      "type": "accessibility",
      "status": "not_determined",
      "name": "辅助功能权限",
      "description": "用于监听键盘和鼠标事件...",
      "required": true,
      "systemSettingsPath": "系统设置 → 隐私与安全性 → 辅助功能"
    },
    "screen_recording": {
      "type": "screen_recording",
      "status": "granted",
      "name": "屏幕录制权限",
      "description": "用于定期截取屏幕快照...",
      "required": true,
      "systemSettingsPath": "系统设置 → 隐私与安全性 → 屏幕录制"
    }
  },
  "platform": "macOS",
  "needsRestart": false
}
```

#### 2. 打开系统设置
```http
POST /api/permissions/open-settings
Body: { "permissionType": "accessibility" }
```

使用 `subprocess.run(["open", "x-apple.systempreferences:..."])` 打开对应的系统设置页面。

#### 3. 请求辅助功能权限
```http
POST /api/permissions/request-accessibility
```

触发系统权限对话框（仅 macOS）。

#### 4. 重启应用
```http
POST /api/permissions/restart-app
Body: { "delaySeconds": 1 }
```

延迟指定秒数后重启应用：
- 对于 `.app` bundle：使用 `open -n app.app`
- 对于直接可执行文件：直接运行可执行文件
- 最后调用 `os._exit(0)` 退出当前进程

## 前端实现

### 状态管理 (`src/lib/stores/permissions.ts`)

```typescript
interface PermissionsState {
  permissionsData: PermissionsCheckResponse | null
  loading: boolean
  error: string | null
  hasChecked: boolean          // 是否已检查过权限
  userDismissed: boolean        // 用户是否关闭了引导

  checkPermissions()
  openSystemSettings(permissionType)
  requestAccessibility()
  restartApp()
  dismissGuide()
  reset()
}
```

**持久化配置:**
- 只持久化 `userDismissed` 状态
- 每次启动时重新检查权限
- 用户关闭引导后的 24 小时内不再显示（可配置）

### UI 组件

#### 1. PermissionsGuide (`src/components/permissions/PermissionsGuide.tsx`)

主要权限引导弹窗，包含：
- **进度指示器**: 显示已授予权限数 / 总权限数
- **权限列表**: 每个权限的状态和操作
- **条件操作栏**:
  - 权限未全部授予：显示"重新检查"和"稍后"按钮
  - 权限已全部授予：显示"重启应用"按钮

**关键特性:**
```typescript
// 首次加载时检查权限
useEffect(() => {
  if (!hasChecked) {
    checkPermissions()
  }
}, [hasChecked, checkPermissions])

// 根据权限状态决定是否显示引导
useEffect(() => {
  if (permissionsData && !userDismissed) {
    setIsVisible(!permissionsData.allGranted)
  }
}, [permissionsData, userDismissed])
```

#### 2. PermissionItem (`src/components/permissions/PermissionItem.tsx`)

单个权限项组件，显示：
- 权限状态图标（✓ / ✗ / ⚠️）
- 权限名称和描述
- 当前状态文本
- "打开设置"按钮（仅当权限未授予时）
- 系统设置路径提示

## 集成方式

### 1. 在主应用中集成 (`src/views/App.tsx`)

```typescript
import { PermissionsGuide } from '@/components/permissions/PermissionsGuide'

function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <div className="h-screen w-screen">
          {renderContent()}
          <PermissionsGuide />  {/* 权限引导弹窗 */}
          <Toaster />
        </div>
      </ThemeProvider>
    </ErrorBoundary>
  )
}
```

### 2. 初始化依赖

在 `pyproject.toml` 中添加：
```toml
dependencies = [
  "pyobjc-framework-quartz>=11.1",  # 用于权限检查
  "numpy>=2.3.0",                   # 用于图像亮度计算
]
```

## 使用流程

### 首次启动用户体验

1. **应用启动** → 触发权限检查
2. **权限引导弹窗显示** → 用户看到权限列表
3. **用户点击"打开设置"** → 系统设置自动打开
4. **用户在系统设置中授予权限** → 返回应用
5. **用户点击"重新检查"** → 验证权限已授予
6. **用户点击"重启应用"** → 应用自动重启
7. **应用重启后正常运行**

### 权限状态流转

```
NOT_DETERMINED (未确定)
       ↓
[用户在系统设置中授予权限]
       ↓
GRANTED (已授予)  或  DENIED (已拒绝)
```

## 权限设置路径

### macOS 系统设置 URL Scheme

**辅助功能权限:**
```
x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility
```

**屏幕录制权限:**
```
x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture
```

打开方式：
```python
subprocess.run([
    "open",
    "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"
])
```

## 故障排除

### 问题 1: 权限检查总是返回 NOT_DETERMINED

**原因:** PyObjC 未安装或版本不兼容

**解决:**
```bash
uv add pyobjc-framework-quartz>=11.1
pnpm setup-backend
pnpm tauri dev
```

### 问题 2: 重启后权限仍未生效

**原因:** 需要完全重启应用（不仅是重载）

**解决:** 当前实现使用 `os._exit(0)` 强制退出，然后启动新进程

### 问题 3: 屏幕录制权限无法检测

**原因:** 截图全黑检测不够准确

**改进方案:**
```python
# 检查文件权限而不是截图内容
import os
from pathlib import Path

def check_screen_recording_via_file():
    # 尝试访问屏幕录制受保护的目录
    protected_path = "/Library/CoreServices/Finder.app"
    try:
        os.listdir(protected_path)
        return PermissionStatus.GRANTED
    except PermissionError:
        return PermissionStatus.DENIED
```

## 国际化支持

### 支持的语言

- **英文** (`en`)
- **中文** (`zh-CN`)

### 翻译结构

```typescript
permissions: {
  status: { granted, denied, notDetermined, restricted, unknown }
  guide: {
    title: "Setup Required Permissions"
    description: "Rewind needs the following permissions..."
    allGrantedMessage: "All permissions granted! ..."
    instructionHint: "Click 'Open Settings' to grant..."
    recheck: "Recheck"
    later: "Later"
    restartApp: "Restart App"
  }
}
```

## 安全考虑

1. **权限检查不会请求权限** - 使用 `kAXTrustedCheckOptionPrompt: False`
2. **用户可以随时关闭引导** - "稍后"按钮允许跳过
3. **自动重启可控制** - `delaySeconds` 参数可配置延迟时间（0-10 秒）
4. **权限状态持久化** - 只记录"用户已关闭"状态，不记录敏感信息

## 扩展功能

### 计划中的改进

1. **定时重新检查**
   ```typescript
   // 每隔 1 小时检查一次权限
   useEffect(() => {
     const interval = setInterval(() => {
       checkPermissions()
     }, 60 * 60 * 1000)
     return () => clearInterval(interval)
   }, [checkPermissions])
   ```

2. **权限通知系统**
   ```typescript
   // 如果权限被收回，显示通知
   if (previousData?.allGranted && !newData.allGranted) {
     toast.warning("Some permissions were revoked")
   }
   ```

3. **Windows/Linux 支持**
   - Windows: 管理员权限检查
   - Linux: X11/Wayland 权限检查

4. **权限日志**
   ```python
   logger.info(f"权限状态变化: {old_status} → {new_status}")
   ```

## 文件列表

### 后端文件
- `backend/models/permissions.py` - 权限相关数据模型
- `backend/system/permissions.py` - 权限检查核心逻辑
- `backend/handlers/permissions.py` - API 端点

### 前端文件
- `src/lib/types/permissions.ts` - TypeScript 类型定义
- `src/lib/stores/permissions.ts` - Zustand 状态管理
- `src/lib/services/permissions/index.ts` - 服务层
- `src/components/permissions/PermissionsGuide.tsx` - 主引导组件
- `src/components/permissions/PermissionItem.tsx` - 权限项组件
- `src/locales/en.ts` - 英文翻译
- `src/locales/zh-CN.ts` - 中文翻译

### 集成文件
- `src/views/App.tsx` - 应用入口集成
- `pyproject.toml` - 依赖配置
- `backend/handlers/__init__.py` - API 注册

## 测试方式

### 本地测试

1. **撤销权限** - 在系统设置中移除 Rewind 的权限
2. **重启应用** - 权限引导应该显示
3. **测试打开设置** - 点击按钮应该打开系统设置
4. **测试重新检查** - 权限状态应该更新
5. **测试自动重启** - 权限全部授予后应该能重启

### API 测试 (FastAPI)

```bash
# 检查权限
curl http://localhost:8000/api/permissions/check

# 打开设置
curl -X POST http://localhost:8000/api/permissions/open-settings \
  -H "Content-Type: application/json" \
  -d '{"permissionType": "accessibility"}'

# 重启应用
curl -X POST http://localhost:8000/api/permissions/restart-app \
  -H "Content-Type: application/json" \
  -d '{"delaySeconds": 2}'
```

## 相关文档

- [macOS 应用启动修复](./app_launch_wrapper.md)
- [代码签名指南](./macos_signing.md)
- [API Handler 系统](./api_handler.md)
- [国际化配置](./i18n.md)

## 许可证

MIT
