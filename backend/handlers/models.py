"""
模型管理处理器
提供多模型配置、选择和管理的 API 端点

功能:
- 创建、列表、更新、删除模型配置
- 选择和切换活跃模型
- 获取活跃模型信息
- 验证模型连接（可选）
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from core.db import get_db
from core.logger import get_logger
from core.settings import get_settings
from . import api_handler
from models.requests import (
    CreateModelRequest,
    UpdateModelRequest,
    SelectModelRequest,
    ModelConfig
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

        # 插入数据库
        db.execute("""
            INSERT INTO llm_models (
                id, name, provider, api_url, model,
                input_token_price, output_token_price, currency,
                api_key, is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            model_id,
            body.name,
            body.provider,
            body.api_url,
            body.model,
            body.input_token_price,
            body.output_token_price,
            body.currency,
            body.api_key,
            False,  # 新创建的模型默认不激活
            now,
            now
        ))
        db.commit()

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

        # 查询所有模型（不返回 api_key）
        cursor = db.execute("""
            SELECT id, name, provider, api_url, model,
                   input_token_price, output_token_price, currency,
                   is_active, created_at, updated_at
            FROM llm_models
            ORDER BY created_at DESC
        """)

        rows = cursor.fetchall()
        models = []

        for row in rows:
            models.append({
                "id": row[0],
                "name": row[1],
                "provider": row[2],
                "apiUrl": row[3],
                "model": row[4],
                "inputTokenPrice": row[5],
                "outputTokenPrice": row[6],
                "currency": row[7],
                "isActive": bool(row[8]),
                "createdAt": row[9],
                "updatedAt": row[10]
            })

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

        cursor = db.execute("""
            SELECT id, name, provider, api_url, model,
                   input_token_price, output_token_price, currency,
                   created_at, updated_at
            FROM llm_models
            WHERE is_active = 1
            LIMIT 1
        """)

        row = cursor.fetchone()

        if not row:
            return {
                "success": False,
                "message": "没有激活的模型",
                "timestamp": datetime.now().isoformat()
            }

        return {
            "success": True,
            "data": {
                "id": row[0],
                "name": row[1],
                "provider": row[2],
                "apiUrl": row[3],
                "model": row[4],
                "inputTokenPrice": row[5],
                "outputTokenPrice": row[6],
                "currency": row[7],
                "createdAt": row[8],
                "updatedAt": row[9]
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
        cursor = db.execute(
            "SELECT id, name FROM llm_models WHERE id = ?",
            (body.model_id,)
        )

        model = cursor.fetchone()
        if not model:
            return {
                "success": False,
                "message": f"模型不存在: {body.model_id}",
                "timestamp": datetime.now().isoformat()
            }

        # 事务：禁用所有其他模型，激活指定模型
        now = datetime.now().isoformat()

        db.execute("UPDATE llm_models SET is_active = 0 WHERE is_active = 1")
        db.execute(
            "UPDATE llm_models SET is_active = 1, updated_at = ? WHERE id = ?",
            (now, body.model_id)
        )
        db.commit()

        logger.info(f"已切换到模型: {body.model_id} ({model[1]})")

        return {
            "success": True,
            "message": f"已切换到模型: {model[1]}",
            "data": {
                "modelId": body.model_id,
                "modelName": model[1]
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


@api_handler(body=UpdateModelRequest)
async def update_model(body: UpdateModelRequest, model_id: str = None) -> Dict[str, Any]:
    """更新模型配置

    注意: 这个处理器接受 URL 参数中的 model_id
    实际调用时需要通过自定义端点处理

    @param body 要更新的字段
    @param model_id 模型 ID
    @returns 更新结果
    """
    # 由于 PyTauri 限制，这个方法需要特殊处理
    # 见下面的 update_model_with_id
    return {
        "success": False,
        "message": "请使用 update_model_with_id 端点",
        "timestamp": datetime.now().isoformat()
    }


async def _update_model_helper(model_id: str, body: UpdateModelRequest) -> Dict[str, Any]:
    """更新模型配置的辅助方法"""
    try:
        db = get_db()

        # 验证模型是否存在
        cursor = db.execute(
            "SELECT id FROM llm_models WHERE id = ?",
            (model_id,)
        )

        if not cursor.fetchone():
            return {
                "success": False,
                "message": f"模型不存在: {model_id}",
                "timestamp": datetime.now().isoformat()
            }

        # 构建更新语句
        updates = []
        params = []

        if body.name is not None:
            updates.append("name = ?")
            params.append(body.name)

        if body.input_token_price is not None:
            updates.append("input_token_price = ?")
            params.append(body.input_token_price)

        if body.output_token_price is not None:
            updates.append("output_token_price = ?")
            params.append(body.output_token_price)

        if body.currency is not None:
            updates.append("currency = ?")
            params.append(body.currency)

        if body.api_key is not None:
            updates.append("api_key = ?")
            params.append(body.api_key)

        if not updates:
            return {
                "success": False,
                "message": "没有要更新的字段",
                "timestamp": datetime.now().isoformat()
            }

        # 添加 updated_at 和 model_id
        now = datetime.now().isoformat()
        updates.append("updated_at = ?")
        params.append(now)
        params.append(model_id)

        # 执行更新
        query = f"UPDATE llm_models SET {', '.join(updates)} WHERE id = ?"
        db.execute(query, params)
        db.commit()

        logger.info(f"模型已更新: {model_id}")

        # 获取更新后的数据
        cursor = db.execute("""
            SELECT id, name, provider, api_url, model,
                   input_token_price, output_token_price, currency,
                   is_active, created_at, updated_at
            FROM llm_models
            WHERE id = ?
        """, (model_id,))

        row = cursor.fetchone()

        return {
            "success": True,
            "message": "模型更新成功",
            "data": {
                "id": row[0],
                "name": row[1],
                "provider": row[2],
                "apiUrl": row[3],
                "model": row[4],
                "inputTokenPrice": row[5],
                "outputTokenPrice": row[6],
                "currency": row[7],
                "isActive": bool(row[8]),
                "createdAt": row[9],
                "updatedAt": row[10]
            },
            "timestamp": now
        }

    except Exception as e:
        logger.error(f"更新模型失败: {e}")
        return {
            "success": False,
            "message": f"更新模型失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


async def _delete_model_helper(model_id: str) -> Dict[str, Any]:
    """删除模型配置的辅助方法"""
    try:
        db = get_db()

        # 验证模型是否存在
        cursor = db.execute(
            "SELECT is_active FROM llm_models WHERE id = ?",
            (model_id,)
        )

        row = cursor.fetchone()
        if not row:
            return {
                "success": False,
                "message": f"模型不存在: {model_id}",
                "timestamp": datetime.now().isoformat()
            }

        was_active = bool(row[0])

        # 删除模型（删除激活模型将使当前没有激活模型）
        db.execute("DELETE FROM llm_models WHERE id = ?", (model_id,))
        db.commit()

        if was_active:
            logger.info(f"激活模型已删除并清空激活状态: {model_id}")
        else:
            logger.info(f"模型已删除: {model_id}")

        return {
            "success": True,
            "message": "模型删除成功",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"删除模型失败: {e}")
        return {
            "success": False,
            "message": f"删除模型失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


# 注意: PyTauri 的 api_handler 装饰器不支持 URL 参数
# 为了支持更新和删除特定模型，我们使用以下方案:
# 1. 在 handlers/__init__.py 中手动注册这些处理器
# 2. 或者在前端调用时使用特定的请求格式

@api_handler(body=UpdateModelRequest)
async def update_model_by_id(body: UpdateModelRequest) -> Dict[str, Any]:
    """更新模型配置 (通过请求体中的 model_id)

    @param body 包含 model_id 和要更新的字段
    @returns 更新结果
    """
    # 这是一个工作区，实际实现需要修改
    return {
        "success": False,
        "message": "需要在前端传递 model_id",
        "timestamp": datetime.now().isoformat()
    }


@api_handler()
async def delete_model(model_id: str) -> Dict[str, Any]:
    """删除模型配置

    @param model_id 要删除的模型 ID
    @returns 删除结果
    """
    try:
        return await _delete_model_helper(model_id)
    except Exception as e:
        logger.error(f"删除模型异常: {e}")
        return {
            "success": False,
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }
