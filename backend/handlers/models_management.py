"""
模型管理处理器（完整版）
支持通过请求体传递所有参数，避免 URL 参数问题
"""

from typing import Dict, Any
from datetime import datetime
import uuid

from core.db import get_db
from core.logger import get_logger
from . import api_handler
from models.requests import (
    CreateModelRequest,
    SelectModelRequest
)

logger = get_logger(__name__)


@api_handler(body=CreateModelRequest)
async def create_model(body: CreateModelRequest) -> Dict[str, Any]:
    """创建新的模型配置

    @param body 模型配置信息（包含API密钥）
    @returns 创建的模型信息
    """
    try:
        db = get_db()

        # 生成唯一 ID
        model_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        insert_query = """
            INSERT INTO llm_models (
                id, name, provider, api_url, model,
                input_token_price, output_token_price, currency,
                api_key, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            model_id,
            body.name,
            body.provider,
            body.api_url,
            body.model,
            body.input_token_price,
            body.output_token_price,
            body.currency,
            body.api_key,
            False,
            now,
            now
        )

        db.execute_insert(insert_query, params)

        logger.info(f"模型已创建: {model_id} ({body.name})")

        return {
            "success": True,
            "message": "模型创建成功",
            "data": {
                "id": model_id,
                "name": body.name,
                "provider": body.provider,
                "model": body.model,
                "currency": body.currency,
                "createdAt": now,
                "isActive": False
            },
            "timestamp": now
        }

    except Exception as e:
        logger.error(f"创建模型失败: {e}")
        return {
            "success": False,
            "message": f"创建模型失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


@api_handler()
async def list_models() -> Dict[str, Any]:
    """获取所有模型配置列表

    @returns 模型列表（不包含API密钥）
    """
    try:
        db = get_db()

        results = db.execute_query("""
            SELECT id, name, provider, api_url, model,
                   input_token_price, output_token_price, currency,
                   is_active, created_at, updated_at
            FROM llm_models
            ORDER BY created_at DESC
        """)

        models = [
            {
                "id": row["id"],
                "name": row["name"],
                "provider": row["provider"],
                "apiUrl": row["api_url"],
                "model": row["model"],
                "inputTokenPrice": row["input_token_price"],
                "outputTokenPrice": row["output_token_price"],
                "currency": row["currency"],
                "isActive": bool(row["is_active"]),
                "createdAt": row["created_at"],
                "updatedAt": row["updated_at"]
            }
            for row in results
        ]

        return {
            "success": True,
            "data": {
                "models": models,
                "count": len(models)
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取模型列表失败: {e}")
        return {
            "success": False,
            "message": f"获取模型列表失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


@api_handler()
async def get_active_model() -> Dict[str, Any]:
    """获取当前激活的模型信息

    @returns 激活模型的详细信息（不包含API密钥）
    """
    try:
        db = get_db()

        row = db.get_active_llm_model()

        if not row:
            return {
                "success": False,
                "message": "没有激活的模型",
                "timestamp": datetime.now().isoformat()
            }

        return {
            "success": True,
            "data": {
                "id": row["id"],
                "name": row["name"],
                "provider": row["provider"],
                "apiUrl": row["api_url"],
                "model": row["model"],
                "inputTokenPrice": row["input_token_price"],
                "outputTokenPrice": row["output_token_price"],
                "currency": row["currency"],
                "createdAt": row["created_at"],
                "updatedAt": row["updated_at"]
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"获取激活模型失败: {e}")
        return {
            "success": False,
            "message": f"获取激活模型失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


@api_handler(body=SelectModelRequest)
async def select_model(body: SelectModelRequest) -> Dict[str, Any]:
    """选择/激活指定的模型

    @param body 包含要激活的模型 ID
    @returns 激活结果和新的模型信息
    """
    try:
        db = get_db()

        # 验证模型是否存在
        results = db.execute_query(
            "SELECT id, name FROM llm_models WHERE id = ?",
            (body.model_id,)
        )

        model = results[0] if results else None
        if not model:
            return {
                "success": False,
                "message": f"模型不存在: {body.model_id}",
                "timestamp": datetime.now().isoformat()
            }

        # 事务：禁用所有其他模型，激活指定模型
        now = datetime.now().isoformat()

        db.execute_update("UPDATE llm_models SET is_active = 0 WHERE is_active = 1")
        db.execute_update(
            "UPDATE llm_models SET is_active = 1, updated_at = ? WHERE id = ?",
            (now, body.model_id)
        )

        logger.info(f"已切换到模型: {body.model_id} ({model['name']})")

        return {
            "success": True,
            "message": f"已切换到模型: {model['name']}",
            "data": {
                "modelId": body.model_id,
                "modelName": model["name"]
            },
            "timestamp": now
        }

    except Exception as e:
        logger.error(f"选择模型失败: {e}")
        return {
            "success": False,
            "message": f"选择模型失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


# 用于更新和删除的通用处理 (通过特殊的请求格式)
class _ModelUpdateBody:
    """内部使用的更新请求模型"""
    pass


class _ModelDeleteBody:
    """内部使用的删除请求模型"""
    pass
