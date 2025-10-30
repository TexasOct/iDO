"""
LLM 总结功能
使用 LLM 对事件进行智能总结

支持图像优化以减少 Token 消耗：
- 智能采样：基于感知哈希检测图像变化
- 内容感知：检测图像内容类型和复杂度
- 混合模式：文本优先，按需添加图像
"""

import asyncio
import os
import base64
from typing import List, Dict, Any, Optional
from datetime import datetime
from core.models import RawRecord, RecordType
from core.logger import get_logger
from llm.client import get_llm_client
from llm.prompt_manager import get_prompt_manager
from processing.image_manager import get_image_manager
from processing.image_optimization import get_image_filter
from processing.image_compression import get_image_optimizer

logger = get_logger(__name__)


class EventSummarizer:
    """事件总结器 - 支持图像优化"""

    def __init__(self, llm_client=None, enable_image_optimization: bool = True):
        """
        Args:
            llm_client: LLM 客户端实例
            enable_image_optimization: 是否启用图像优化
        """
        self.llm_client = llm_client or get_llm_client()
        self.prompt_manager = get_prompt_manager()
        self.summary_cache = {}  # 缓存总结结果
        self.image_manager = get_image_manager()

        # 图像优化
        self.enable_image_optimization = enable_image_optimization
        self.image_filter = None
        self.image_optimizer = None
        if enable_image_optimization:
            try:
                self.image_filter = get_image_filter()
                self.image_optimizer = get_image_optimizer()
                logger.info("图像优化已启用（包含高级压缩）")
            except Exception as e:
                logger.warning(f"初始化图像优化失败: {e}，将禁用优化")
                self.enable_image_optimization = False

    def encode_image(self, image_path: str) -> Optional[str]:
        """将图片编码为base64"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"图片编码失败 {image_path}: {e}")
            return None

    def build_flexible_messages(self,
                              content_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        构建灵活的消息格式，支持任意顺序的文字和图片

        Args:
            content_items: 内容项列表，每个项包含type和content
                          type可以是'text'或'image'，content是文字内容或图片路径

        Returns:
            构建好的消息列表
        """
        content = []
        image_count = 0
        max_images = 20  # 限制图片数量避免请求过大

        for item in content_items:
            if item['type'] == 'text':
                content.append({
                    "type": "text",
                    "text": item['content']
                })
            elif item['type'] == 'image' and image_count < max_images:
                img_data = item['content']
                if img_data:
                    # 对于图片，需要构建正确的格式
                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_data}"
                        }
                    })
                    image_count += 1
            elif item['type'] == 'image' and image_count >= max_images:
                logger.warning(f"达到最大图片数量限制 ({max_images})，跳过图片内容")

        logger.debug(f"构建消息完成: {len(content)} 个内容项，其中 {image_count} 个图片")

        return [{
            "role": "user",
            "content": content
        }]

    def _build_input_usage_hint(
        self,
        keyboard_stats: Dict[str, int],
        mouse_stats: Dict[str, int]
    ) -> str:
        """根据键鼠统计生成辅助描述，返回简短提示"""
        summary_parts: List[str] = []

        keyboard_total = keyboard_stats.get("total", 0)
        if keyboard_total:
            keyboard_desc = f"检测到 {keyboard_total} 次键盘输入"
            modifiers = keyboard_stats.get("with_modifiers", 0)
            special = keyboard_stats.get("special", 0)

            if modifiers:
                keyboard_desc += f"，其中 {modifiers} 次使用了修饰键"
            if special:
                keyboard_desc += f"，包含 {special} 次特殊按键"

            summary_parts.append(f"键盘活动：{keyboard_desc}")

        mouse_total = mouse_stats.get("total", 0)
        if mouse_total:
            mouse_details: List[str] = []
            click = mouse_stats.get("click", 0)
            scroll = mouse_stats.get("scroll", 0)
            drag = mouse_stats.get("drag", 0)

            if click:
                mouse_details.append(f"点击 {click} 次")
            if scroll:
                mouse_details.append(f"滚动 {scroll} 次")
            if drag:
                mouse_details.append(f"拖拽 {drag} 次")

            if mouse_details:
                mouse_desc = "，".join(mouse_details)
            else:
                mouse_desc = f"检测到 {mouse_total} 次鼠标操作"

            summary_parts.append(f"鼠标活动：{mouse_desc}")

        if not summary_parts:
            return ""

        return "；".join(summary_parts)

    async def summarize_events(self, events: List[RawRecord]) -> str:
        """
        总结事件列表 - 支持图像优化

        当启用图像优化时，会：
        1. 检测重复图像（感知哈希）
        2. 分析图像内容复杂度
        3. 限制采样频率和数量
        4. 记录优化统计信息
        """
        if not events:
            return "无事件"

        try:
            # 按时间排序事件
            sorted_events = sorted(events, key=lambda x: x.timestamp)

            # 重置优化统计（每次总结重新开始）
            if self.enable_image_optimization and self.image_filter:
                self.image_filter.reset()

            # 构建内容项列表，仅向 LLM 提供截图原始记录
            content_items = []
            screenshot_count = 0
            is_first_screenshot = True
            keyboard_stats = {
                "total": 0,
                "with_modifiers": 0,
                "special": 0
            }
            mouse_stats = {
                "total": 0,
                "click": 0,
                "scroll": 0,
                "drag": 0
            }

            for event in sorted_events:
                if event.type == RecordType.KEYBOARD_RECORD:
                    data = event.data or {}
                    keyboard_stats["total"] += 1
                    if data.get("modifiers"):
                        keyboard_stats["with_modifiers"] += 1
                    if str(data.get("key_type", "")).lower() == "special":
                        keyboard_stats["special"] += 1
                    continue

                if event.type == RecordType.MOUSE_RECORD:
                    data = event.data or {}
                    mouse_stats["total"] += 1
                    action = data.get("action", "")
                    if action in {"press", "release", "click"}:
                        mouse_stats["click"] += 1
                    elif action == "scroll":
                        mouse_stats["scroll"] += 1
                    elif action in {"drag", "drag_end"}:
                        mouse_stats["drag"] += 1
                    continue

                if event.type == RecordType.SCREENSHOT_RECORD:
                    # 图片信息 - 可能被优化过滤
                    img_data = self._get_record_image_data(event)
                    if not img_data:
                        continue

                    # 应用图像优化过滤器
                    if self.enable_image_optimization and self.image_filter:
                        img_bytes = base64.b64decode(img_data)
                        event_id = f"event_{id(event)}"
                        current_time = event.timestamp.timestamp()

                        should_include, reason = self.image_filter.should_include_image(
                            img_bytes=img_bytes,
                            event_id=event_id,
                            current_time=current_time,
                            is_first=is_first_screenshot
                        )

                        is_first_screenshot = False

                        if should_include:
                            # 应用高级压缩（如果启用）
                            final_img_data = img_data
                            if self.image_optimizer:
                                try:
                                    optimized_bytes, opt_meta = self.image_optimizer.optimize(
                                        img_bytes,
                                        is_first=(screenshot_count == 0)
                                    )
                                    final_img_data = base64.b64encode(optimized_bytes).decode('utf-8')

                                    logger.debug(
                                        f"图像压缩: {opt_meta.get('original_tokens', 0)} tokens → "
                                        f"{opt_meta.get('optimized_tokens', 0)} tokens "
                                        f"(节省 {opt_meta.get('tokens_saved', 0)})"
                                    )
                                except Exception as e:
                                    logger.warning(f"图像压缩失败，使用原图: {e}")
                                    final_img_data = img_data

                            content_items.append({
                                "type": "image",
                                "content": final_img_data
                            })
                            screenshot_count += 1
                            logger.debug(f"包含截图: {reason}")
                        else:
                            logger.debug(f"跳过截图: {reason}")
                    else:
                        # 未启用优化，直接包含
                        content_items.append({
                            "type": "image",
                            "content": img_data
                        })
                        screenshot_count += 1

            input_usage_hint = self._build_input_usage_hint(keyboard_stats, mouse_stats)
            if not input_usage_hint:
                input_usage_hint = "当前时间段未检测到明显的键盘或鼠标操作"

            prompt_text = self.prompt_manager.get_user_prompt(
                "event_summarization",
                "user_prompt_template",
                input_usage_hint=input_usage_hint
            )

            if not prompt_text:
                prompt_text = f"辅助提示：{input_usage_hint}"

            content_items.insert(0, {
                "type": "text",
                "content": prompt_text
            })

            if not content_items:
                return "无有效内容"

            # 构建消息并调用LLM
            messages = self.build_flexible_messages(content_items)

            # 添加系统提示
            system_prompt = self.prompt_manager.get_system_prompt("event_summarization")
            messages.insert(0, {
                "role": "system",
                "content": system_prompt
            })

            # 获取配置参数
            config_params = self.prompt_manager.get_config_params("event_summarization")

            # 调用LLM API
            response = await self.llm_client.chat_completion(messages, **config_params)
            summary = response.get("content", "总结失败")

            # 记录优化统计
            if self.enable_image_optimization and self.image_filter:
                self.image_filter.log_summary()

            # 记录压缩统计
            if self.enable_image_optimization and self.image_optimizer:
                compression_stats = self.image_optimizer.get_stats()
                if compression_stats['images_processed'] > 0:
                    logger.info(
                        f"图像压缩统计: 处理 {compression_stats['images_processed']} 张, "
                        f"Token 节省 {compression_stats['tokens']['saved']} "
                        f"({compression_stats['tokens']['reduction_percentage']:.1f}%)"
                    )

            if summary.startswith("API 请求失败") or summary.startswith("API 调用异常"):
                fallback = self._fallback_summary(content_items)
                logger.warning(f"LLM 总结失败，启用本地回退: {summary}")
                return f"[Fallback] {fallback}"

            logger.debug(f"事件总结完成: {summary}")
            return summary

        except Exception as e:
            logger.error(f"事件总结失败: {e}")
            return f"总结失败: {str(e)}"

    def _get_record_image_data(self, record: RawRecord) -> Optional[str]:
        """获取截图记录的base64数据，支持内存缓存和磁盘回退"""
        try:
            data = record.data or {}
            # 1. 直接读取记录中携带的base64
            img_data = data.get("img_data")
            if img_data:
                return img_data

            # 2. 通过图片哈希从内存缓存获取
            img_hash = data.get("hash")
            if img_hash:
                img_hash = str(img_hash)
                cached = self.image_manager.get_from_memory_cache(img_hash)
                if cached:
                    return cached

                # 3. 回退：尝试从磁盘缩略图加载
                thumbnail_path = self._resolve_thumbnail_path(img_hash)
                if thumbnail_path and os.path.exists(thumbnail_path):
                    with open(thumbnail_path, "rb") as img_file:
                        img_bytes = img_file.read()
                    return self.image_manager.add_to_memory_cache(img_hash, img_bytes)

            # 4. 最后尝试使用 screenshot_path（可能在某些环境下已存在）
            screenshot_path = data.get("screenshotPath") or record.screenshot_path
            if screenshot_path and os.path.exists(screenshot_path):
                with open(screenshot_path, "rb") as img_file:
                    img_bytes = img_file.read()
                cache_key = img_hash or os.path.basename(screenshot_path)
                return self.image_manager.add_to_memory_cache(cache_key, img_bytes)

        except Exception as e:
            logger.warning(f"获取截图数据失败: {e}")

        return None

    def _resolve_thumbnail_path(self, img_hash: str) -> Optional[str]:
        """根据哈希推断缩略图路径"""
        if not img_hash:
            return None
        filename = f"thumb_{img_hash[:12]}.jpg"
        return str(self.image_manager.thumbnails_dir / filename)

    def _fallback_summary(self, content_items: List[Dict[str, Any]]) -> str:
        """构建本地回退总结"""
        texts = [item["content"] for item in content_items if item["type"] == "text" and item.get("content")]
        image_count = sum(1 for item in content_items if item["type"] == "image")

        parts: List[str] = []
        if texts:
            preview = "; ".join(texts[:5])
            if len(texts) > 5:
                preview += " 等"
            parts.append(f"键鼠操作: {preview}")
        if image_count:
            parts.append(f"包含 {image_count} 张屏幕截图")

        return "；".join(parts) if parts else "记录有限，暂未生成总结"

    async def summarize_activity(self, activity_events: List[RawRecord]) -> str:
        """总结活动事件"""
        if not activity_events:
            return "无活动"

        try:
            # 分析活动模式
            activity_pattern = self._analyze_activity_pattern(activity_events)

            # 生成活动总结
            summary = await self._generate_activity_summary(activity_pattern)

            logger.debug(f"活动总结完成: {summary}")
            return summary

        except Exception as e:
            logger.error(f"活动总结失败: {e}")
            return f"活动总结失败: {str(e)}"

    def _group_events_by_type(self, events: List[RawRecord]) -> Dict[RecordType, List[RawRecord]]:
        """按类型分组事件"""
        grouped = {}
        for event in events:
            if event.type not in grouped:
                grouped[event.type] = []
            grouped[event.type].append(event)
        return grouped

    async def _summarize_event_type(self, event_type: RecordType, events: List[RawRecord]) -> str:
        """总结特定类型的事件"""
        if not events:
            return ""

        try:
            if event_type == RecordType.KEYBOARD_RECORD:
                return await self._summarize_keyboard_events(events)
            elif event_type == RecordType.MOUSE_RECORD:
                return await self._summarize_mouse_events(events)
            elif event_type == RecordType.SCREENSHOT_RECORD:
                return await self._summarize_screenshot_events(events)
            else:
                return f"未知事件类型: {event_type.value}"

        except Exception as e:
            logger.error(f"总结 {event_type.value} 事件失败: {e}")
            return f"总结失败: {str(e)}"

    async def _summarize_keyboard_events(self, events: List[RawRecord]) -> str:
        """总结键盘事件"""
        if not events:
            return ""

        # 分析键盘事件模式
        key_sequence = []
        modifiers_used = set()
        special_keys = []

        for event in events:
            data = event.data
            key = data.get("key", "")
            action = data.get("action", "")
            modifiers = data.get("modifiers", [])

            if action == "press":
                key_sequence.append(key)
                modifiers_used.update(modifiers)

                if data.get("key_type") == "special":
                    special_keys.append(key)

        # 生成总结
        summary_parts = []

        if special_keys:
            summary_parts.append(f"按了特殊键: {', '.join(special_keys)}")

        if modifiers_used:
            summary_parts.append(f"使用了修饰键: {', '.join(modifiers_used)}")

        if len(key_sequence) > 5:
            summary_parts.append(f"输入了 {len(key_sequence)} 个字符")
        elif key_sequence:
            summary_parts.append(f"输入序列: {''.join(key_sequence[:10])}")

        if not summary_parts:
            summary_parts.append("进行了键盘操作")

        return "键盘: " + "; ".join(summary_parts)

    async def _summarize_mouse_events(self, events: List[RawRecord]) -> str:
        """总结鼠标事件"""
        if not events:
            return ""

        # 分析鼠标事件模式
        click_count = 0
        scroll_count = 0
        drag_count = 0
        positions = []

        for event in events:
            data = event.data
            action = data.get("action", "")
            position = data.get("position")

            if action in ["press", "release"]:
                click_count += 1
            elif action == "scroll":
                scroll_count += 1
            elif action in ["drag", "drag_end"]:
                drag_count += 1

            if position:
                positions.append(position)

        # 生成总结
        summary_parts = []

        if click_count > 0:
            summary_parts.append(f"点击了 {click_count} 次")

        if scroll_count > 0:
            summary_parts.append(f"滚动了 {scroll_count} 次")

        if drag_count > 0:
            summary_parts.append(f"拖拽了 {drag_count} 次")

        if positions:
            # 计算移动范围
            x_coords = [pos[0] for pos in positions if len(pos) >= 2]
            y_coords = [pos[1] for pos in positions if len(pos) >= 2]

            if x_coords and y_coords:
                x_range = max(x_coords) - min(x_coords)
                y_range = max(y_coords) - min(y_coords)
                summary_parts.append(f"移动范围: {x_range:.0f}x{y_range:.0f} 像素")

        if not summary_parts:
            summary_parts.append("进行了鼠标操作")

        return "鼠标: " + "; ".join(summary_parts)

    async def _summarize_screenshot_events(self, events: List[RawRecord]) -> str:
        """总结屏幕截图事件"""
        if not events:
            return ""

        # 分析屏幕截图模式
        total_size = 0
        dimensions = set()
        time_span = 0

        if events:
            first_time = events[0].timestamp
            last_time = events[-1].timestamp
            time_span = (last_time - first_time).total_seconds()

            for event in events:
                data = event.data
                total_size += data.get("size_bytes", 0)
                width = data.get("width", 0)
                height = data.get("height", 0)
                if width > 0 and height > 0:
                    dimensions.add((width, height))

        # 生成总结
        summary_parts = []

        if len(events) > 1:
            summary_parts.append(f"截取了 {len(events)} 张图片")
        else:
            summary_parts.append("截取了 1 张图片")

        if dimensions:
            dim_str = ", ".join([f"{w}x{h}" for w, h in sorted(dimensions)])
            summary_parts.append(f"尺寸: {dim_str}")

        if total_size > 0:
            size_mb = total_size / (1024 * 1024)
            summary_parts.append(f"总大小: {size_mb:.1f}MB")

        if time_span > 0:
            summary_parts.append(f"时间跨度: {time_span:.1f}秒")

        return "屏幕: " + "; ".join(summary_parts)

    def _analyze_activity_pattern(self, events: List[RawRecord]) -> Dict[str, Any]:
        """分析活动模式"""
        pattern = {
            "total_events": len(events),
            "event_types": {},
            "time_span": 0,
            "keyboard_activity": 0,
            "mouse_activity": 0,
            "screenshot_activity": 0,
            "intensity": "low"
        }

        if not events:
            return pattern

        # 计算时间跨度
        first_time = min(event.timestamp for event in events)
        last_time = max(event.timestamp for event in events)
        pattern["time_span"] = (last_time - first_time).total_seconds()

        # 统计各类型事件
        for event in events:
            event_type = event.type.value
            pattern["event_types"][event_type] = pattern["event_types"].get(event_type, 0) + 1

            if event.type == RecordType.KEYBOARD_RECORD:
                pattern["keyboard_activity"] += 1
            elif event.type == RecordType.MOUSE_RECORD:
                pattern["mouse_activity"] += 1
            elif event.type == RecordType.SCREENSHOT_RECORD:
                pattern["screenshot_activity"] += 1

        # 计算活动强度
        events_per_second = pattern["total_events"] / max(pattern["time_span"], 1)
        if events_per_second > 2:
            pattern["intensity"] = "high"
        elif events_per_second > 0.5:
            pattern["intensity"] = "medium"

        return pattern

    async def _generate_activity_summary(self, pattern: Dict[str, Any]) -> str:
        """生成活动总结"""
        summary_parts = []

        # 活动强度
        intensity = pattern.get("intensity", "low")
        if intensity == "high":
            summary_parts.append("高强度活动")
        elif intensity == "medium":
            summary_parts.append("中等强度活动")
        else:
            summary_parts.append("低强度活动")

        # 时间跨度
        time_span = pattern.get("time_span", 0)
        if time_span > 60:
            summary_parts.append(f"持续 {time_span/60:.1f} 分钟")
        elif time_span > 0:
            summary_parts.append(f"持续 {time_span:.1f} 秒")

        # 事件类型分布
        event_types = pattern.get("event_types", {})
        type_descriptions = []

        if event_types.get("keyboard_event", 0) > 0:
            type_descriptions.append(f"键盘操作 {event_types['keyboard_event']} 次")

        if event_types.get("mouse_event", 0) > 0:
            type_descriptions.append(f"鼠标操作 {event_types['mouse_event']} 次")

        if event_types.get("screenshot", 0) > 0:
            type_descriptions.append(f"屏幕截图 {event_types['screenshot']} 次")

        if type_descriptions:
            summary_parts.append("包含: " + ", ".join(type_descriptions))

        return "; ".join(summary_parts)

    async def _merge_summaries(self, summaries: List[str]) -> str:
        """合并多个总结"""
        if not summaries:
            return "无事件"

        if len(summaries) == 1:
            return summaries[0]

        # 简单的合并逻辑
        return " | ".join(summaries)

    def clear_cache(self):
        """清空缓存"""
        self.summary_cache.clear()
        logger.debug("总结缓存已清空")
