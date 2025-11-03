# 权限系统测试指南

## 快速开始

### 1. 安装依赖

```bash
# 安装 Python 依赖
pnpm setup-backend

# 或手动同步
uv sync
```

### 2. 启动开发环境

```bash
# 启动 Tauri 开发版本
pnpm tauri dev

# 或只启动 FastAPI（用于 API 测试）
uv run python app.py
```

## 测试场景

### 场景 1: 首次启动（无权限）

**步骤:**
1. 在系统设置中撤销 Rewind 对辅助功能的权限
2. 在系统设置中撤销 Rewind 对屏幕录制的权限
3. 启动应用

**预期结果:**
- ✓ 权限引导弹窗显示
- ✓ 显示两个权限都未授予（红色 ✗）
- ✓ 进度条显示 0/2
- ✓ "重新检查"和"稍后"按钮可用

### 场景 2: 部分权限已授予

**步骤:**
1. 授予辅助功能权限，但不授予屏幕录制权限
2. 启动应用

**预期结果:**
- ✓ 权限引导弹窗显示
- ✓ 辅助功能权限显示绿色 ✓
- ✓ 屏幕录制权限显示红色 ✗
- ✓ 进度条显示 1/2
- ✓ 只能点击屏幕录制权限的"打开设置"

### 场景 3: 所有权限已授予

**步骤:**
1. 授予所有必需权限
2. 启动应用

**预期结果:**
- ✓ 权限引导仍然显示
- ✓ 两个权限都显示绿色 ✓
- ✓ 进度条显示 2/2
- ✓ 显示"所有权限已授予！请重启应用以使其生效"消息
- ✓ "重启应用"按钮可用

### 场景 4: 打开系统设置

**步骤:**
1. 权限引导显示
2. 点击某个权限的"打开设置"按钮

**预期结果:**
- ✓ 系统设置应用自动打开
- ✓ 打开对应的权限设置页面（辅助功能或屏幕录制）

### 场景 5: 重新检查权限

**步骤:**
1. 权限引导显示，部分权限未授予
2. 点击"打开设置"按钮
3. 在系统设置中授予权限
4. 返回到应用
5. 点击"重新检查"按钮

**预期结果:**
- ✓ 权限状态立即更新
- ✓ 图标从 ✗ 变为 ✓
- ✓ 进度条更新
- ✓ 当所有权限都授予时，显示"已授予"消息和"重启应用"按钮

### 场景 6: 自动重启

**步骤:**
1. 所有权限都已授予
2. 点击"重启应用"按钮
3. 观察应用行为

**预期结果:**
- ✓ 显示"正在重启应用..."提示
- ✓ 应用在 1 秒后关闭
- ✓ 应用重新启动
- ✓ 权限引导不再显示（因为权限已授予）

### 场景 7: 关闭引导（稍后）

**步骤:**
1. 权限引导显示
2. 点击"稍后"按钮

**预期结果:**
- ✓ 权限引导关闭
- ✓ 应用继续运行
- ✓ 下次启动应用时，不再显示引导（基于 localStorage）

## API 测试

### 使用 FastAPI 直接测试

启动 FastAPI 服务器：
```bash
uv run python app.py
# 或
uvicorn app:app --reload
```

访问 Swagger UI: http://localhost:8000/docs

### 测试 1: 检查权限

```bash
curl -X GET http://localhost:8000/api/permissions/check
```

**响应示例:**
```json
{
  "allGranted": false,
  "permissions": {
    "accessibility": {
      "type": "accessibility",
      "status": "not_determined",
      "name": "辅助功能权限",
      "description": "用于监听键盘和鼠标事件，记录您的活动轨迹",
      "required": true,
      "systemSettingsPath": "系统设置 → 隐私与安全性 → 辅助功能"
    },
    "screen_recording": {
      "type": "screen_recording",
      "status": "granted",
      "name": "屏幕录制权限",
      "description": "用于定期截取屏幕快照，帮助您回顾工作内容",
      "required": true,
      "systemSettingsPath": "系统设置 → 隐私与安全性 → 屏幕录制"
    }
  },
  "platform": "macOS",
  "needsRestart": false
}
```

### 测试 2: 打开系统设置

```bash
curl -X POST http://localhost:8000/api/permissions/open-settings \
  -H "Content-Type: application/json" \
  -d '{"permissionType": "accessibility"}'
```

**响应:**
```json
{
  "success": true,
  "message": "已打开 accessibility 权限设置页面"
}
```

### 测试 3: 请求辅助功能权限

```bash
curl -X POST http://localhost:8000/api/permissions/request-accessibility
```

**响应:**
```json
{
  "success": true,
  "granted": true,
  "message": "辅助功能权限已授予"
}
```

### 测试 4: 重启应用

```bash
curl -X POST http://localhost:8000/api/permissions/restart-app \
  -H "Content-Type: application/json" \
  -d '{"delaySeconds": 2}'
```

**响应:**
```json
{
  "success": true,
  "message": "应用将在 2 秒后重启",
  "delaySeconds": 2
}
```

## 调试技巧

### 查看权限检查日志

在后端代码中添加日志：
```python
import logging
logger = logging.getLogger(__name__)

logger.info(f"权限检查完成: {result}")
logger.debug(f"辅助功能权限: {accessibility_status}")
logger.debug(f"屏幕录制权限: {screen_recording_status}")
```

### 在浏览器控制台检查状态

```javascript
// 在浏览器 DevTools 中运行
import { usePermissionsStore } from '@/lib/stores/permissions'
const store = usePermissionsStore.getState()
console.log(store.permissionsData)
console.log(store.userDismissed)
```

### 清除持久化状态

```javascript
// 在浏览器控制台中运行
localStorage.removeItem('rewind-permissions')
location.reload()
```

### 查看网络请求

在 DevTools 的 Network 标签页中：
1. 打开应用
2. 观察对 `/api/permissions/check` 的请求
3. 检查响应数据结构

## 性能测试

### 权限检查延迟

权限检查应该在 100ms 内完成：

```typescript
const start = performance.now()
await checkPermissions()
const duration = performance.now() - start
console.log(`权限检查耗时: ${duration}ms`)
```

### UI 响应时间

- 权限引导显示: < 100ms
- 权限项渲染: < 50ms 每个
- 状态更新: < 200ms

## 边界条件测试

### 1. 网络延迟

使用 DevTools 的 Network throttling 来模拟延迟：
- 设置为 "Slow 3G"
- 检查权限引导是否显示加载状态
- 检查是否有超时处理

### 2. 权限更改

在权限检查进行中时改变系统权限：
- 应该继续完成当前请求
- 下次检查应该反映新的状态

### 3. 连续重启

点击"重启应用"多次：
- 第一个请求应该成功
- 后续请求应该被拒绝（应用已关闭）

## 兼容性测试

### macOS 版本

测试以下 macOS 版本：
- [ ] macOS 12 (Monterey)
- [ ] macOS 13 (Ventura)
- [ ] macOS 14 (Sonoma)
- [ ] macOS 15 (Sequoia)

### Python 版本

项目需要 Python 3.14+

```bash
python --version
# Python 3.14.x
```

## 回归测试清单

在每次修改权限系统后运行：

- [ ] 权限引导正确显示
- [ ] 权限状态正确判断
- [ ] 打开设置正常工作
- [ ] 重新检查权限更新状态
- [ ] 自动重启工作正常
- [ ] 国际化文本正确显示
- [ ] 响应式设计在各尺寸下工作
- [ ] 深色/浅色主题都正常显示
- [ ] 没有控制台错误或警告

## 常见问题排查

### Q: 权限检查总是返回 NOT_DETERMINED

**A:**
1. 检查 PyObjC 是否安装: `python -c "from Quartz import AXIsProcessTrustedWithOptions"`
2. 确保 Rewind 不在信任列表中（在系统设置中移除）
3. 重启应用

### Q: 打开设置按钮不工作

**A:**
1. 检查是否在 macOS 上
2. 查看后端日志是否有错误
3. 尝试手动运行: `open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"`

### Q: 重启应用后权限仍未生效

**A:**
1. 确保应用完全退出（检查活动监视器）
2. 增加延迟时间: `delaySeconds: 3`
3. 检查是否在 `.app` bundle 中运行

### Q: 屏幕录制权限检测不准确

**A:**
1. 目前使用亮度检测，可能不完全准确
2. 尝试实现基于文件权限的检测
3. 或使用 `tccutil` 命令行工具

## 提交测试报告

运行以上所有测试后，创建一个测试报告：

```markdown
# 权限系统测试报告

## 测试日期
- 2024-XX-XX

## 测试环境
- macOS 版本:
- Python 版本:
- 应用版本:

## 测试结果
- [x] 场景 1: 首次启动
- [x] 场景 2: 部分权限
- [x] 场景 3: 全部权限
- [ ] ...

## 发现的问题
1. 问题描述
2. 复现步骤
3. 预期行为 vs 实际行为

## 性能指标
- 权限检查延迟: XXms
- UI 响应时间: XXms

## 建议
- ...
```

## 相关文档

- [权限引导系统](./permissions_guide.md)
- [macOS 应用启动修复](./app_launch_wrapper.md)
- [开发指南](./development.md)
