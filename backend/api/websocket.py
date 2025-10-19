"""
WebSocket 实时推送
实现基础的 WebSocket 广播机制
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List, Dict, Any
import json
import asyncio
from core.logger import get_logger

logger = get_logger(__name__)

# WebSocket 连接管理器
class ConnectionManager:
    """WebSocket 连接管理器"""
    
    def __init__(self):
        # 存储所有活跃连接
        self.active_connections: List[WebSocket] = []
        # 存储连接信息
        self.connection_info: Dict[WebSocket, Dict[str, Any]] = {}
    
    async def connect(self, websocket: WebSocket, client_info: Dict[str, Any] = None):
        """接受新的 WebSocket 连接"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_info[websocket] = client_info or {}
        logger.info(f"新的 WebSocket 连接已建立，当前连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """断开 WebSocket 连接"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.connection_info:
            del self.connection_info[websocket]
        logger.info(f"WebSocket 连接已断开，当前连接数: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """发送个人消息"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"发送个人消息失败: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        """广播消息给所有连接"""
        if not self.active_connections:
            return
        
        # 创建任务列表
        tasks = []
        disconnected = []
        
        for connection in self.active_connections:
            try:
                task = asyncio.create_task(connection.send_text(message))
                tasks.append(task)
            except Exception as e:
                logger.error(f"广播消息失败: {e}")
                disconnected.append(connection)
        
        # 清理断开的连接
        for connection in disconnected:
            self.disconnect(connection)
        
        # 等待所有发送任务完成
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_json(self, data: Dict[str, Any]):
        """广播 JSON 数据给所有连接"""
        message = json.dumps(data, ensure_ascii=False)
        await self.broadcast(message)
    
    def get_connection_count(self) -> int:
        """获取当前连接数"""
        return len(self.active_connections)


# 全局连接管理器实例
manager = ConnectionManager()

# 创建 WebSocket 路由器
websocket_router = APIRouter()


@websocket_router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 端点"""
    client_info = {
        "client_ip": websocket.client.host if websocket.client else "unknown",
        "user_agent": websocket.headers.get("user-agent", "unknown")
    }
    
    await manager.connect(websocket, client_info)
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            logger.debug(f"收到 WebSocket 消息: {data}")
            
            # 处理客户端消息
            try:
                message_data = json.loads(data)
                await handle_client_message(websocket, message_data)
            except json.JSONDecodeError:
                logger.warning(f"无效的 JSON 消息: {data}")
                await manager.send_personal_message(
                    json.dumps({"error": "Invalid JSON format"}), 
                    websocket
                )
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket 连接错误: {e}")
        manager.disconnect(websocket)


async def handle_client_message(websocket: WebSocket, message_data: Dict[str, Any]):
    """处理客户端消息"""
    message_type = message_data.get("type", "unknown")
    
    if message_type == "ping":
        # 心跳检测
        await manager.send_personal_message(
            json.dumps({"type": "pong", "timestamp": message_data.get("timestamp")}),
            websocket
        )
    
    elif message_type == "subscribe":
        # 订阅特定事件类型
        event_type = message_data.get("event_type", "all")
        # TODO: 实现订阅逻辑
        await manager.send_personal_message(
            json.dumps({"type": "subscribed", "event_type": event_type}),
            websocket
        )
    
    else:
        # 未知消息类型
        await manager.send_personal_message(
            json.dumps({"error": f"Unknown message type: {message_type}"}),
            websocket
        )


# 广播函数（供其他模块调用）
async def broadcast_activity(activity_data: Dict[str, Any]):
    """广播活动数据"""
    message = {
        "type": "activity",
        "data": activity_data,
        "timestamp": activity_data.get("timestamp")
    }
    await manager.broadcast_json(message)
    logger.debug(f"广播活动数据: {activity_data.get('id', 'unknown')}")


async def broadcast_task(task_data: Dict[str, Any]):
    """广播任务数据"""
    message = {
        "type": "task",
        "data": task_data,
        "timestamp": task_data.get("timestamp")
    }
    await manager.broadcast_json(message)
    logger.debug(f"广播任务数据: {task_data.get('id', 'unknown')}")


async def broadcast_system_status(status_data: Dict[str, Any]):
    """广播系统状态"""
    message = {
        "type": "system_status",
        "data": status_data,
        "timestamp": status_data.get("timestamp")
    }
    await manager.broadcast_json(message)
    logger.debug("广播系统状态")


# 获取连接统计信息
def get_connection_stats() -> Dict[str, Any]:
    """获取连接统计信息"""
    return {
        "active_connections": manager.get_connection_count(),
        "connection_info": list(manager.connection_info.values())
    }
