"""
LLM 总结功能
使用 LLM 对事件进行智能总结
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

logger = get_logger(__name__)


class EventSummarizer:
    """事件总结器"""
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client or get_llm_client()
        self.prompt_manager = get_prompt_manager()
        self.summary_cache = {}  # 缓存总结结果
    
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
                print(f"警告: 已达到最大图片数量限制 ({max_images})，跳过图片: {item['content']}")
        
        print(f"构建消息完成: {len(content)} 个内容项，其中 {image_count} 个图片")
        
        return [{
            "role": "user",
            "content": content
        }]
    
    def _format_record_as_text(self, record: RawRecord) -> str:
        """将记录格式化为文本"""
        if record.type == RecordType.KEYBOARD_RECORD:
            data = record.data
            key = data.get("key", "")
            action = data.get("action", "")
            modifiers = data.get("modifiers", [])
            
            if action == "press":
                modifier_str = "+".join(modifiers) if modifiers else ""
                if modifier_str:
                    return f"[键盘] {modifier_str}+{key}"
                else:
                    return f"[键盘] {key}"
            return ""
        
        elif record.type == RecordType.MOUSE_RECORD:
            data = record.data
            action = data.get("action", "")
            position = data.get("position", [])
            
            if action in ["press", "release"]:
                button = data.get("button", "left")
                return f"[鼠标] {action} {button} 键"
            elif action == "scroll":
                delta = data.get("delta", [0, 0])
                return f"[鼠标] 滚动 {delta[1]:.1f}"
            elif action in ["drag", "drag_end"]:
                return f"[鼠标] {action}"
            return ""
        
        return ""
    
    async def summarize_events(self, events: List[RawRecord]) -> str:
        """总结事件列表"""
        if not events:
            return "无事件"
        
        try:
            # 按时间排序事件
            sorted_events = sorted(events, key=lambda x: x.timestamp)
            
            # 构建内容项列表，按时间交错排列text和image
            content_items = []
            for event in sorted_events:
                if event.type == RecordType.KEYBOARD_RECORD or event.type == RecordType.MOUSE_RECORD:
                    # 文本信息
                    text_content = self._format_record_as_text(event)
                    if text_content:
                        content_items.append({
                            "type": "text",
                            "content": text_content
                        })
                elif event.type == RecordType.SCREENSHOT_RECORD:
                    # 图片信息
                    img_data = event.data.get("img_data")
                    if img_data:
                        content_items.append({
                            "type": "image",
                            "content": img_data
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
            
            logger.debug(f"事件总结完成: {summary}")
            return summary
                
        except Exception as e:
            logger.error(f"事件总结失败: {e}")
            return f"总结失败: {str(e)}"
    
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
