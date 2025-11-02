"""
后端流程协调器
负责协调 PerceptionManager 和 ProcessingPipeline 的完整生命周期
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from core.logger import get_logger
from config.loader import get_config
from core.db import get_db

logger = get_logger(__name__)

# 全局协调器实例
_coordinator: Optional['PipelineCoordinator'] = None


class PipelineCoordinator:
    """流程协调器"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化协调器

        Args:
            config: 配置字典
        """
        self.config = config
        self.processing_interval = config.get('monitoring.processing_interval', 30)
        self.window_size = config.get('monitoring.window_size', 60)
        self.capture_interval = config.get('monitoring.capture_interval', 0.2)

        # 初始化管理器（延迟导入避免循环依赖）
        self.perception_manager = None
        self.processing_pipeline = None

        # 运行状态
        self.is_running = False
        self.processing_task: Optional[asyncio.Task] = None
        self.mode: str = "stopped"  # running | stopped | requires_model | error | starting
        self.last_error: Optional[str] = None
        self.active_model: Optional[Dict[str, Any]] = None

        # 统计信息
        self.stats = {
            "start_time": None,
            "total_processing_cycles": 0,
            "last_processing_time": None,
            "perception_stats": {},
            "processing_stats": {}
        }

    def _set_state(self, *, mode: str, error: Optional[str] = None) -> None:
        """更新协调器状态字段"""
        self.mode = mode
        self.last_error = error
        if error:
            logger.debug("Coordinator state updated: mode=%s, error=%s", mode, error)
        else:
            logger.debug("Coordinator state updated: mode=%s", mode)

    def _sanitize_active_model(self, model: Dict[str, Any]) -> Dict[str, Any]:
        """构建用于前端展示的激活模型信息，移除敏感字段"""
        sanitized = {
            "id": model.get("id"),
            "name": model.get("name") or model.get("model"),
            "provider": model.get("provider"),
            "model": model.get("model"),
            "last_test_status": bool(model.get("last_test_status")),
            "last_tested_at": model.get("last_tested_at"),
            "last_test_error": model.get("last_test_error"),
            "updated_at": model.get("updated_at"),
        }
        return sanitized

    def _refresh_active_model(self) -> None:
        """刷新当前激活模型信息，保持状态与数据库同步"""
        try:
            db = get_db()
            active_model = db.get_active_llm_model()
            if active_model:
                sanitized = self._sanitize_active_model(active_model)
                self.active_model = sanitized
                if not sanitized.get("last_test_status"):
                    message = sanitized.get("last_test_error") or "激活模型尚未通过 API 测试，请先在模型管理中点击测试按钮。"
                    if self.mode != "requires_model" or self.last_error != message:
                        self._set_state(mode="requires_model", error=message)
            else:
                self.active_model = None
        except Exception as exc:
            logger.debug("刷新激活模型信息失败: %s", exc)

    def _ensure_active_model(self) -> Optional[Dict[str, Any]]:
        """确保存在激活的 LLM 模型配置，缺失时返回 None"""
        try:
            db = get_db()
            active_model = db.get_active_llm_model()
            if not active_model:
                message = "未检测到激活的 LLM 模型配置，请在设置中添加并激活模型。"
                self._set_state(mode="requires_model", error=message)
                self.active_model = None
                logger.warning(message)
                return None
            required_fields = ['api_key', 'api_url', 'model']
            missing = [field for field in required_fields if not active_model.get(field)]
            if missing:
                message = f"激活的模型配置缺少必要字段: {', '.join(missing)}，请在设置中补全后重新启动。"
                self._set_state(mode="requires_model", error=message)
                self.active_model = None
                logger.warning(message)
                return None

            sanitized = self._sanitize_active_model(active_model)
            self.active_model = sanitized

            # 如果模型未通过测试，仅记录警告但仍允许系统启动
            if not sanitized.get("last_test_status"):
                message = sanitized.get("last_test_error") or "激活模型尚未通过连通性测试，建议在模型管理中点击测试按钮验证配置。"
                logger.warning(message)
                # 注意：不再设置为 requires_model 模式，允许系统继续启动

            return active_model
        except Exception as exc:
            message = f"无法读取激活的 LLM 模型配置: {exc}"
            logger.error(message)
            self._set_state(mode="error", error=message)
            self.active_model = None
            return None

    def _init_managers(self):
        """延迟初始化管理器"""
        if self.perception_manager is None:
            from perception.manager import PerceptionManager
            self.perception_manager = PerceptionManager(
                capture_interval=self.capture_interval,
                window_size=self.window_size
            )

        if self.processing_pipeline is None:
            from processing.pipeline import ProcessingPipeline
            processing_config = self.config.get('processing', {})
            language_config = self.config.get('language', {})
            self.processing_pipeline = ProcessingPipeline(
                screenshot_threshold=processing_config.get("event_extraction_threshold", 20),
                activity_summary_interval=processing_config.get("activity_summary_interval", 600),
                knowledge_merge_interval=processing_config.get("knowledge_merge_interval", 1200),
                todo_merge_interval=processing_config.get("todo_merge_interval", 1200),
                language=language_config.get("default_language", "zh"),
                enable_screenshot_deduplication=processing_config.get("enable_screenshot_deduplication", True)
            )

    def ensure_managers_initialized(self):
        """对外暴露的初始化入口"""
        self._init_managers()

    async def start(self) -> None:
        """启动整个流程"""
        if self.is_running:
            logger.warning("协调器已在运行中")
            return

        try:
            self._set_state(mode="starting", error=None)
            logger.info("正在启动流程协调器...")

            # 初始化管理器
            active_model = self._ensure_active_model()
            if not active_model:
                # 无可用模型时保持受限模式，不抛出异常，允许前端继续渲染
                logger.warning("流程协调器未启动：缺少有效的 LLM 模型配置")
                self.is_running = False
                self.processing_task = None
                self.stats["start_time"] = None
                self.stats["last_processing_time"] = None
                return

            logger.info(
                "检测到激活模型配置: %s (%s)",
                active_model.get('name') or active_model.get('model'),
                active_model.get('provider')
            )
            self._init_managers()

            if not self.perception_manager:
                logger.error("感知管理器初始化失败")
                raise Exception("感知管理器初始化失败")

            if not self.processing_pipeline:
                logger.error("处理管道初始化失败")
                raise Exception("处理管道初始化失败")

            # 并行启动感知管理器和处理管道（它们是独立的）
            logger.debug("正在并行启动感知管理器和处理管道...")
            start_time = datetime.now()

            await asyncio.gather(
                self.perception_manager.start(),
                self.processing_pipeline.start()
            )

            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"感知管理器和处理管道已启动 (耗时 {elapsed:.2f}s)")

            # 启动定时处理循环
            self.is_running = True
            self._set_state(mode="running", error=None)
            self.processing_task = asyncio.create_task(self._processing_loop())
            self.stats["start_time"] = datetime.now()

            logger.info(f"流程协调器已启动，处理间隔: {self.processing_interval} 秒")

        except Exception as e:
            logger.error(f"启动协调器失败: {e}")
            await self.stop()
            raise

    async def stop(self, *, quiet: bool = False) -> None:
        """停止整个流程

        Args:
            quiet: 为 True 时仅记录调试日志，避免在终端输出停机提示。
        """
        if not self.is_running:
            self._set_state(mode="stopped", error=None)
            self.processing_task = None
            return

        try:
            log = logger.debug if quiet else logger.info
            log("正在停止流程协调器...")

            # 停止定时处理循环
            self.is_running = False
            if self.processing_task and not self.processing_task.done():
                self.processing_task.cancel()
                try:
                    await self.processing_task
                except asyncio.CancelledError:
                    pass
            self.processing_task = None

            # 停止处理管道
            if self.processing_pipeline:
                await self.processing_pipeline.stop()
                log("处理管道已停止")

            # 停止感知管理器
            if self.perception_manager:
                await self.perception_manager.stop()
                log("感知管理器已停止")

            log("流程协调器已停止")

        except Exception as e:
            logger.error(f"停止协调器失败: {e}")
        finally:
            self._set_state(mode="stopped", error=None)
            self.is_running = False
            self.processing_task = None

    async def _processing_loop(self) -> None:
        """定时处理循环"""
        try:
            # 第一次处理延迟较短，之后使用正常间隔
            first_iteration = True

            while self.is_running:
                # 第一次迭代快速启动（100ms），之后使用配置的间隔
                wait_time = 0.1 if first_iteration else self.processing_interval
                await asyncio.sleep(wait_time)

                if not self.is_running:
                    break

                first_iteration = False

                if not self.perception_manager:
                    logger.error("感知管理器未初始化")
                    raise Exception("感知管理器未初始化")

                if not self.processing_pipeline:
                    logger.error("处理管道未初始化")
                    raise Exception("处理管道未初始化")

                # 获取最近 processing_interval 秒内的记录
                records = self.perception_manager.get_records_in_last_n_seconds(self.processing_interval)

                if records:
                    logger.debug(f"开始处理 {len(records)} 条记录")

                    # 处理记录
                    result = await self.processing_pipeline.process_raw_records(records)

                    # 更新统计
                    self.stats["total_processing_cycles"] += 1
                    self.stats["last_processing_time"] = datetime.now()

                    logger.debug(f"处理完成: {len(result.get('events', []))} 个事件, {len(result.get('activities', []))} 个活动")
                else:
                    logger.debug("没有新记录需要处理")

        except asyncio.CancelledError:
            logger.debug("处理循环已取消")
        except Exception as e:
            logger.error(f"处理循环失败: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """获取协调器统计信息"""
        try:
            self._refresh_active_model()
            # 获取各组件统计
            perception_stats = {}
            processing_stats = {}

            if self.perception_manager:
                perception_stats = self.perception_manager.get_stats()

            if self.processing_pipeline:
                processing_stats = self.processing_pipeline.get_stats()

            # 合并统计信息
            stats = {
                "coordinator": {
                    "is_running": self.is_running,
                    "status": self.mode,
                    "last_error": self.last_error,
                    "active_model": self.active_model,
                    "processing_interval": self.processing_interval,
                    "window_size": self.window_size,
                    "capture_interval": self.capture_interval,
                    "start_time": self.stats["start_time"].isoformat() if self.stats["start_time"] else None,
                    "total_processing_cycles": self.stats["total_processing_cycles"],
                    "last_processing_time": self.stats["last_processing_time"].isoformat() if self.stats["last_processing_time"] else None
                },
                "perception": perception_stats,
                "processing": processing_stats
            }

            return stats

        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {"error": str(e)}


def get_coordinator() -> PipelineCoordinator:
    """获取全局协调器单例"""
    global _coordinator
    if _coordinator is None:
        config = get_config().load()

        _coordinator = PipelineCoordinator(config)
    return _coordinator
