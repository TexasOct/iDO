"""
数据持久化接口
处理 events 和 activities 的数据库存储
"""

import json
from typing import List, Dict, Any
from datetime import datetime, timedelta
from core.models import Event, RecordType
from core.logger import get_logger
from core.db import get_db
from processing.image_manager import get_image_manager

logger = get_logger(__name__)


class ProcessingPersistence:
    """处理数据持久化器"""

    def __init__(self):
        self.db = get_db()
        self.image_manager = get_image_manager()

    def _convert_event_type(self, event_type_str: str) -> 'RecordType':
        """转换事件类型字符串为新的 RecordType 枚举"""
        from core.models import RecordType
        type_mapping = {
            "keyboard_event": RecordType.KEYBOARD_RECORD,
            "mouse_event": RecordType.MOUSE_RECORD,
            "screenshot": RecordType.SCREENSHOT_RECORD,
            # 新格式
            "keyboard_record": RecordType.KEYBOARD_RECORD,
            "mouse_record": RecordType.MOUSE_RECORD,
            "screenshot_record": RecordType.SCREENSHOT_RECORD,
        }
        return type_mapping.get(event_type_str, RecordType.KEYBOARD_RECORD)

    async def save_event(self, event: Event) -> bool:
        """保存事件到数据库（不持久化图片）"""
        try:
            # 准备事件数据（移除 base64 图片数据）
            source_data_cleaned = []
            for record in event.source_data:
                record_dict = record.to_dict()

                # 如果是截图记录，移除 img_data（保留在内存中）
                if record.type == RecordType.SCREENSHOT_RECORD and "data" in record_dict:
                    data_copy = record_dict["data"].copy()
                    data_copy.pop("img_data", None)  # 移除 base64 数据
                    record_dict["data"] = data_copy

                source_data_cleaned.append(record_dict)

            event_data = {
                "id": event.id,
                "start_time": event.start_time.isoformat(),
                "end_time": event.end_time.isoformat(),
                "summary": event.summary,
                "source_data": source_data_cleaned
            }

            # 插入到数据库
            self.db.insert_event(
                event_id=event.id,
                start_time=event_data["start_time"],
                end_time=event_data["end_time"],
                event_type="",  # type字段已废弃，保留空字符串以兼容数据库结构
                summary=event.summary,
                source_data=event_data["source_data"]
            )

            logger.debug(f"事件已保存: {event.id}")
            return True

        except Exception as e:
            logger.error(f"保存事件失败: {e}")
            return False

    async def save_activity(self, activity: Dict[str, Any]) -> bool:
        """保存活动到数据库并发送事件通知前端（持久化截图为缩略图）"""
        try:
            # 处理截图：批量尝试从内存缓存获取图片数据，回退到磁盘缩略图或临时路径，最后再记录警告
            screenshot_hashes_persisted = set()
            persisted_images: Dict[str, Dict[str, Any]] = {}

            # 先收集所有唯一的截图哈希
            unique_hashes: List[str] = []
            record_map: Dict[str, List[Dict[str, Any]]] = {}
            for event in activity.get("source_events", []):
                for record in event.source_data:
                    if record.type == RecordType.SCREENSHOT_RECORD:
                        raw_hash = record.data.get("hash")
                        if not raw_hash:
                            continue
                        img_hash = str(raw_hash)
                        if img_hash not in unique_hashes:
                            unique_hashes.append(img_hash)
                        record_map.setdefault(img_hash, []).append(record)

            if unique_hashes:
                # 批量从内存缓存获取（减少多次单独查询）
                cache_results = self.image_manager.get_multiple_from_cache(unique_hashes)

                import base64
                from pathlib import Path

                for img_hash in unique_hashes:
                    if img_hash in screenshot_hashes_persisted:
                        continue

                    # 1) 优先使用内存缓存的原始图片数据进行持久化
                    img_data_b64 = cache_results.get(img_hash)
                    if img_data_b64:
                        try:
                            img_bytes = base64.b64decode(img_data_b64)
                            result = self.image_manager.persist_image(img_hash, img_bytes, keep_original=False)
                            if result.get("success"):
                                persisted_images[img_hash] = result
                                logger.debug(
                                    f"截图已持久化为缩略图: {img_hash[:8]}, 大小: {result['thumbnail_size']/1024:.1f}KB"
                                )
                                screenshot_hashes_persisted.add(img_hash)
                                # 移除内存缓存项（persist_image 会尝试移除）
                                continue
                            else:
                                logger.warning(f"持久化截图失败: {img_hash[:8]}, 原因: {result}")
                        except Exception as e:
                            logger.warning(f"解码或持久化内存缓存图片失败: {img_hash[:8]} - {e}")

                    # 2) 内存缓存没有，则尝试加载已有的磁盘缩略图（如果已存在）
                    try:
                        thumb_b64 = self.image_manager.load_thumbnail_base64(img_hash)
                        if thumb_b64:
                            # 已存在缩略图，无需再次生成，记录缩略图路径和大小
                            thumbnail_path = self.image_manager.get_thumbnail_path(img_hash)
                            try:
                                file_size = Path(thumbnail_path).stat().st_size if thumbnail_path else 0
                            except Exception:
                                file_size = 0
                            persisted_images[img_hash] = {
                                "success": True,
                                "thumbnail_path": thumbnail_path,
                                "thumbnail_size": file_size,
                                "hash": img_hash
                            }
                            logger.debug(f"已找到磁盘缩略图: {img_hash[:8]} -> {thumbnail_path}")
                            screenshot_hashes_persisted.add(img_hash)
                            continue
                    except Exception as e:
                        logger.debug(f"尝试从磁盘加载缩略图失败: {img_hash[:8]} - {e}")

                    # 3) 回退：检查对应记录中是否包含临时路径（screenshotPath / screenshot_path），并尝试读取该文件以持久化
                    fallback_done = False
                    for rec in record_map.get(img_hash, []):
                        try:
                            rec_data = getattr(rec, "data", {}) if hasattr(rec, "data") else rec.get("data", {})
                            tmp_path = (
                                rec_data.get("screenshotPath")
                                or rec_data.get("screenshot_path")
                                or getattr(rec, "screenshot_path", None)
                            )
                            if tmp_path:
                                p = Path(tmp_path)
                                if p.exists() and p.is_file():
                                    try:
                                        with p.open("rb") as f:
                                            file_bytes = f.read()
                                        result = self.image_manager.persist_image(img_hash, file_bytes, keep_original=False)
                                        if result.get("success"):
                                            persisted_images[img_hash] = result
                                            logger.debug(
                                                f"从临时文件持久化截图: {img_hash[:8]} -> {result.get('thumbnail_path')}"
                                            )
                                            screenshot_hashes_persisted.add(img_hash)
                                            fallback_done = True
                                            break
                                    except Exception as e:
                                        logger.debug(f"读取临时截图文件或持久化失败: {tmp_path} - {e}")
                        except Exception:
                            continue

                    if fallback_done:
                        continue

                    # 4) 如果都没有找到，则推迟记录警告，后续在生成活动数据时再做更精确的提示或保留原路径
                    logger.debug(f"未在内存/磁盘/临时路径找到截图数据（可后续回退处理）: {img_hash[:8]}")

            # 结束批量处理，接下来 persisted_images 与 screenshot_hashes_persisted 可被后续代码使用

            # 准备活动数据（移除 base64 图片数据）
            source_events_cleaned = []
            for event in activity.get("source_events", []):
                event_dict = event.to_dict()

                # 清理 source_data 中的图片数据
                source_data_cleaned = []
                for record in event.source_data:
                    record_dict = record.to_dict()

                    if record.type == RecordType.SCREENSHOT_RECORD and "data" in record_dict:
                        data_copy = record_dict["data"].copy()
                        data_copy.pop("img_data", None)  # 移除 base64 数据

                        img_hash = data_copy.get("hash")
                        if img_hash is not None:
                            img_hash = str(img_hash)
                        thumbnail_info = persisted_images.get(img_hash) if img_hash else None
                        thumbnail_path = None
                        if thumbnail_info:
                            thumbnail_path = thumbnail_info.get("thumbnail_path")

                        if thumbnail_path:
                            # 更新记录中的 screenshot path，为前端提供可访问的缩略图路径
                            data_copy["screenshotPath"] = thumbnail_path
                            record_dict["screenshot_path"] = thumbnail_path
                        else:
                            # 如果未成功持久化，尝试保留原路径（可能已存在文件）
                            existing_path = (
                                data_copy.get("screenshotPath")
                                or data_copy.get("screenshot_path")
                                or record_dict.get("screenshot_path")
                            )
                            if existing_path:
                                data_copy["screenshotPath"] = existing_path
                                record_dict["screenshot_path"] = existing_path
                            else:
                                # 清理无效路径字段，避免前端加载失败
                                data_copy.pop("screenshotPath", None)
                                data_copy.pop("screenshot_path", None)
                                record_dict.pop("screenshot_path", None)

                        record_dict["data"] = data_copy

                    source_data_cleaned.append(record_dict)

                event_dict["source_data"] = source_data_cleaned
                source_events_cleaned.append(event_dict)

            activity_data = {
                "id": activity["id"],
                "title": activity.get("title", ""),
                "description": activity["description"],
                "start_time": activity["start_time"].isoformat() if isinstance(activity["start_time"], datetime) else activity["start_time"],
                "end_time": activity["end_time"].isoformat() if isinstance(activity["end_time"], datetime) else activity["end_time"],
                "source_events": source_events_cleaned,
                "event_count": activity.get("event_count", 0),
                "created_at": activity.get("created_at", datetime.now()).isoformat()
            }

            # 插入到数据库
            self.db.insert_activity(
                activity_id=activity["id"],
                title=activity.get("title", ""),
                description=activity["description"],
                start_time=activity_data["start_time"],
                end_time=activity_data["end_time"],
                source_events=activity_data["source_events"]
            )

            logger.debug(f"活动已保存: {activity['id']} - {activity.get('title', '')}")

            # 获取当前版本号用于通知
            max_version = self.db.get_max_activity_version()

            # 发送事件通知前端进行增量更新
            try:
                from core.events import emit_activity_created
                emit_activity_created({
                    **activity_data,
                    "version": max_version
                })
            except Exception as e:
                logger.warning(f"发送活动创建事件失败（前端可能不会实时接收通知）: {e}")

            return True

        except Exception as e:
            logger.error(f"保存活动失败: {e}")
            return False

    async def get_recent_events(self, limit: int = 50) -> List[Event]:
        """获取最近的事件"""
        try:
            # 从数据库获取事件数据
            events_data = self.db.get_events(limit=limit)

            events = []
            for event_data in events_data:
                try:
                    # 解析源数据
                    source_data = []
                    if event_data.get("source_data"):
                        source_data_json = json.loads(event_data["source_data"]) if isinstance(event_data["source_data"], str) else event_data["source_data"]
                        for record_data in source_data_json:
                            from core.models import RawRecord, RecordType
                            source_data.append(RawRecord(
                                timestamp=datetime.fromisoformat(record_data["timestamp"]),
                                type=RecordType(record_data["type"]),
                                data=record_data["data"]
                            ))

                    # 创建事件对象
                    event = Event(
                        id=event_data["id"],
                        start_time=datetime.fromisoformat(event_data["start_time"]),
                        end_time=datetime.fromisoformat(event_data["end_time"]),
                        summary=event_data["summary"],
                        source_data=source_data
                    )
                    events.append(event)

                except Exception as e:
                    logger.error(f"解析事件数据失败: {e}")
                    continue

            logger.debug(f"获取到 {len(events)} 个事件")
            return events

        except Exception as e:
            logger.error(f"获取最近事件失败: {e}")
            return []

    async def get_recent_activities(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的活动"""
        try:
            # 从数据库获取活动数据
            activities_data = self.db.get_activities(limit=limit)

            activities = []
            for activity_data in activities_data:
                try:
                    # 解析源事件
                    source_events = []
                    if activity_data.get("source_events"):
                        source_events_json = json.loads(activity_data["source_events"]) if isinstance(activity_data["source_events"], str) else activity_data["source_events"]
                        for event_data in source_events_json:
                            # 这里简化处理，实际应该重建完整的 Event 对象
                            source_events.append(event_data)

                    # 创建活动字典
                    activity = {
                        "id": activity_data["id"],
                        "title": activity_data.get("title", ""),
                        "description": activity_data["description"],
                        "start_time": datetime.fromisoformat(activity_data["start_time"]),
                        "end_time": datetime.fromisoformat(activity_data["end_time"]),
                        "source_events": source_events,
                        "created_at": datetime.fromisoformat(activity_data["created_at"]) if activity_data.get("created_at") else datetime.now()
                    }
                    activities.append(activity)

                except Exception as e:
                    logger.error(f"解析活动数据失败: {e}")
                    continue

            logger.debug(f"获取到 {len(activities)} 个活动")
            return activities

        except Exception as e:
            logger.error(f"获取最近活动失败: {e}")
            return []

    async def get_events_by_type(self, event_type: str, limit: int = 50) -> List[Event]:
        """根据类型获取事件"""
        try:
            # 从数据库获取指定类型的事件
            events_data = self.db.execute_query(
                "SELECT * FROM events WHERE type = ? ORDER BY start_time DESC LIMIT ?",
                (event_type, limit)
            )

            events = []
            for event_data in events_data:
                try:
                    # 解析源数据
                    source_data = []
                    if event_data.get("source_data"):
                        source_data_json = json.loads(event_data["source_data"]) if isinstance(event_data["source_data"], str) else event_data["source_data"]
                        for record_data in source_data_json:
                            from core.models import RawRecord, RecordType
                            source_data.append(RawRecord(
                                timestamp=datetime.fromisoformat(record_data["timestamp"]),
                                type=RecordType(record_data["type"]),
                                data=record_data["data"]
                            ))

                    # 创建事件对象
                    event = Event(
                        id=event_data["id"],
                        start_time=datetime.fromisoformat(event_data["start_time"]),
                        end_time=datetime.fromisoformat(event_data["end_time"]),
                        summary=event_data["summary"],
                        source_data=source_data
                    )
                    events.append(event)

                except Exception as e:
                    logger.error(f"解析事件数据失败: {e}")
                    continue

            logger.debug(f"获取到 {len(events)} 个 {event_type} 事件")
            return events

        except Exception as e:
            logger.error(f"获取 {event_type} 事件失败: {e}")
            return []


    async def get_events_in_timeframe(self, start_time: datetime, end_time: datetime) -> List[Event]:
        """获取指定时间范围内的事件"""
        try:
            # 从数据库获取时间范围内的事件
            events_data = self.db.execute_query(
                "SELECT * FROM events WHERE start_time >= ? AND end_time <= ? ORDER BY start_time DESC",
                (start_time.isoformat(), end_time.isoformat())
            )

            events = []
            for event_data in events_data:
                try:
                    # 解析源数据
                    source_data = []
                    if event_data.get("source_data"):
                        source_data_json = json.loads(event_data["source_data"]) if isinstance(event_data["source_data"], str) else event_data["source_data"]
                        for record_data in source_data_json:
                            from core.models import RawRecord, RecordType
                            source_data.append(RawRecord(
                                timestamp=datetime.fromisoformat(record_data["timestamp"]),
                                type=RecordType(record_data["type"]),
                                data=record_data["data"]
                            ))

                    # 创建事件对象
                    event = Event(
                        id=event_data["id"],
                        start_time=datetime.fromisoformat(event_data["start_time"]),
                        end_time=datetime.fromisoformat(event_data["end_time"]),
                        summary=event_data["summary"],
                        source_data=source_data
                    )
                    events.append(event)

                except Exception as e:
                    logger.error(f"解析事件数据失败: {e}")
                    continue

            logger.debug(f"获取到 {len(events)} 个时间范围内的事件")
            return events

        except Exception as e:
            logger.error(f"获取时间范围内事件失败: {e}")
            return []

    async def delete_old_data(self, days: int = 30):
        """删除旧数据"""
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            cutoff_str = cutoff_date.isoformat()

            # 删除旧事件
            deleted_events = self.db.execute_delete(
                "DELETE FROM events WHERE start_time < ?",
                (cutoff_str,)
            )

            # 删除旧活动
            deleted_activities = self.db.execute_delete(
                "DELETE FROM activities WHERE start_time < ?",
                (cutoff_str,)
            )

            logger.info(f"删除了 {deleted_events} 个旧事件和 {deleted_activities} 个旧活动")
            return {"events": deleted_events, "activities": deleted_activities}

        except Exception as e:
            logger.error(f"删除旧数据失败: {e}")
            return {"events": 0, "activities": 0}

    def get_stats(self) -> Dict[str, Any]:
        """获取持久化统计信息"""
        try:
            # 获取事件统计
            event_count = self.db.execute_query("SELECT COUNT(*) as count FROM events")[0]["count"]

            # 获取活动统计
            activity_count = self.db.execute_query("SELECT COUNT(*) as count FROM activities")[0]["count"]

            # 获取最近事件时间
            recent_event = self.db.execute_query(
                "SELECT start_time FROM events ORDER BY start_time DESC LIMIT 1"
            )
            last_event_time = recent_event[0]["start_time"] if recent_event else None

            # 获取最近活动时间
            recent_activity = self.db.execute_query(
                "SELECT start_time FROM activities ORDER BY start_time DESC LIMIT 1"
            )
            last_activity_time = recent_activity[0]["start_time"] if recent_activity else None

            return {
                "total_events": event_count,
                "total_activities": activity_count,
                "last_event_time": last_event_time,
                "last_activity_time": last_activity_time
            }

        except Exception as e:
            logger.error(f"获取持久化统计失败: {e}")
            return {
                "total_events": 0,
                "total_activities": 0,
                "last_event_time": None,
                "last_activity_time": None
            }
