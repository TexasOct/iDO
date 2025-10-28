# 特殊说明（Special Notes）

本文件列出 Rewind 项目中需要被开发者注意的重要约定、限制和操作要点。将项目级别的「注意事项」集中到这里，便于在 README 中保持简介，同时在 docs 中提供可查阅的细节。

## 开发与配置约定
- TypeScript 严格模式：项目启用了严格的 TypeScript 配置，请在新增代码时留意类型校验（noImplicitAny、strictNullChecks 等）。
- 路径别名：代码中使用 `@/*` 作为 `src/` 的路径别名，IDE 和构建工具需配置一致。
- 主题系统：使用 `next-themes`（或等效方案）管理深色/浅色主题；UI 组件应对主题切换保持样式一致。
- 表单验证：推荐使用 React Hook Form + Zod，保持表单校验集中且可复用。
- 错误边界：重要页面或布局组件应使用 Error Boundaries 以避免整个应用崩溃。

## 生成文件与不要编辑
- 自动生成客户端：`src/lib/client/` 为 PyTauri / 后端自动生成的 TypeScript 客户端，绝对不要手动编辑。如果后端变更，按流程重新生成客户端。
- shadcn/ui 组件：`src/components/shadcn-ui/` 由生成工具产出，按工具文档维护；不直接手改生成文件。
- 自动类型：`src/types/auto-imports.d.ts` 等为自动生成产物，不要手动修改。

## PyTauri / 后端处理器要求（关键）
- 所有带参数的 PyTauri/FastAPI handler 必须只接受一个 `body` 参数，并使用 Pydantic 模型进行验证。
  - 正确： `def handler(body: MyRequest)`（其中 `MyRequest` 为 Pydantic）
  - 错误： `def handler(name: str, id: int)`（PyTauri 不支持此签名）
- 修改或新增后端 handler / Pydantic 模型后：
  1. 在项目根运行后端环境同步（例如 `uv sync` 或 `pnpm setup-backend`）。
  2. 重新生成 / 重建以触发 TypeScript 客户端生成（通常通过 `pnpm tauri dev` 或相应流程）。

## Python 环境（重要）
- `pyproject.toml` 位于项目根（不是 `src-tauri/`）。
- 虚拟环境 `.venv` 会在项目根创建（`uv sync` 时）；所有与 Python 相关的同步、安装、依赖管理需在项目根执行。
- 在 CI / 本地开发中，务必在项目根运行 `uv sync` / `pnpm setup-backend` 来保证 Python 依赖与客户端同步一致。

## i18n（翻译）约定
- 英文文件 `src/locales/en.ts` 为键结构的来源（source of truth），其它语言必须镜像其 key 结构。
- 使用 `pnpm check-i18n` 校验翻译文件一致性，CI 中强烈建议启用该校验。

## 活动时间线（Activity Timeline）注意点
- 实时更新：使用 Tauri 事件推送（如 `activity-created`），前端在 UI 层做去抖（debounce）与合并处理（例如 300ms 批处理）。
- 安全时间解析：所有时间戳需防御性解析，遇到无效时间应降级到 `Date.now()` 或合适的回退值。
- UI 稳定性：新增活动应有入场动画但保持与已有条目样式一致；长列表需使用虚拟化/分页以保持性能。

## 隐私与安全（原则性）
- 最小化持久化敏感数据：尽量以元数据、hash 或摘要形式存储，避免将原始的按键记录或未脱敏截图长期保存在 DB 中。
- 明确用户控制：提供明显的开关用于启/停数据采集，记录/显示正在采集的状态。
- 环境变量与密钥：不要将 API Key 或私密信息提交到仓库。使用 `.env`（或 CI secret）管理，且提供 `.env.example` 供本地参考。

## 性能与成本控制（建议）
- 批量处理：后端应对原始记录做批量处理（例如每 10 秒）以减少对 LLM 的调用频率与成本。
- 截图与图像优化：后端对截图做压缩与感知哈希去重，避免冗余存储与重复处理。
- 前端限内存：timeline 等视图在内存中仅保留最近必要的区块（例如最多 100 个日期块），历史数据按需分页加载。

## CI / 变更后流程（简要）
- 修改后端 handler / 模型 → 在项目根运行后端同步（`uv sync` / `pnpm setup-backend`）→ 重新生成 TypeScript 客户端（通过 tauri dev/build 流程）→ 更新前端调用并运行测试/lint/i18n 校验。
- 在 PR 描述中明确列出后端变更、生成客户端动作、及需要 reviewer 额外注意的点（如模型字段变更或 key 重命名）。

## 快速检查清单（简短）
- [ ] 新增后端 handler？-> 添加 Pydantic，import 到 `backend/handlers/__init__.py`，运行 `pnpm setup-backend`。
- [ ] 修改模型字段？-> 重新生成 TypeScript 客户端并运行前端编译检查。
- [ ] 修改翻译 key？-> 先修改 `src/locales/en.ts`，再更新其它语言并运行 `pnpm check-i18n`。
- [ ] 改动影响 UI 性能？-> 确保长列表虚拟化或分页，运行性能 smoke test。

---

如需，我可以把本文件内容再精简成 README 中的短版提示，或生成一个更详细的「变更后流程 checklist」文档用于团队 PR 模板与 CI。
