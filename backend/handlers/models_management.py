"""
模型管理处理器（完整版）
支持通过请求体传递所有参数，避免 URL 参数问题
"""

from typing import Dict, Any
from datetime import datetime
import uuid
import httpx

from core.db import get_db
from core.logger import get_logger
from core.coordinator import get_coordinator
from system.runtime import start_runtime, stop_runtime
from . import api_handler
from models.requests import (
    CreateModelRequest,
    UpdateModelRequest,
    DeleteModelRequest,
    SelectModelRequest,
    TestModelRequest
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


@api_handler(body=UpdateModelRequest)
async def update_model(body: UpdateModelRequest) -> Dict[str, Any]:
    """更新模型配置

    @param body 要更新的模型信息（只更新提供的字段）
    @returns 更新后的模型信息
    """
    try:
        db = get_db()

        # 验证模型是否存在
        results = db.execute_query(
            "SELECT id, name, api_key FROM llm_models WHERE id = ?",
            (body.model_id,)
        )

        if not results:
            return {
                "success": False,
                "message": f"模型不存在: {body.model_id}",
                "timestamp": datetime.now().isoformat()
            }

        existing_model = results[0]
        now = datetime.now().isoformat()

        # 构建更新语句（只更新提供的字段）
        update_fields = []
        params = []

        if body.name is not None:
            update_fields.append("name = ?")
            params.append(body.name)

        if body.provider is not None:
            update_fields.append("provider = ?")
            params.append(body.provider)

        if body.api_url is not None:
            update_fields.append("api_url = ?")
            params.append(body.api_url)

        if body.model is not None:
            update_fields.append("model = ?")
            params.append(body.model)

        if body.input_token_price is not None:
            update_fields.append("input_token_price = ?")
            params.append(body.input_token_price)

        if body.output_token_price is not None:
            update_fields.append("output_token_price = ?")
            params.append(body.output_token_price)

        if body.currency is not None:
            update_fields.append("currency = ?")
            params.append(body.currency)

        # 如果提供了 API Key，则更新；否则保留原有的
        if body.api_key is not None and body.api_key.strip():
            update_fields.append("api_key = ?")
            params.append(body.api_key)

        # 总是更新 updated_at
        update_fields.append("updated_at = ?")
        params.append(now)

        # 添加 WHERE 条件
        params.append(body.model_id)

        if not update_fields:
            return {
                "success": False,
                "message": "没有提供要更新的字段",
                "timestamp": now
            }

        update_query = f"""
            UPDATE llm_models
            SET {', '.join(update_fields)}
            WHERE id = ?
        """

        db.execute_update(update_query, tuple(params))

        logger.info(f"模型已更新: {body.model_id} ({body.name or existing_model['name']})")

        # 获取更新后的模型信息
        updated_results = db.execute_query("""
            SELECT id, name, provider, api_url, model,
                   input_token_price, output_token_price, currency,
                   is_active, last_test_status, last_tested_at, last_test_error,
                   created_at, updated_at
            FROM llm_models
            WHERE id = ?
        """, (body.model_id,))

        if updated_results:
            row = updated_results[0]
            return {
                "success": True,
                "message": "模型更新成功",
                "data": {
                    "id": row["id"],
                    "name": row["name"],
                    "provider": row["provider"],
                    "apiUrl": row["api_url"],
                    "model": row["model"],
                    "inputTokenPrice": row["input_token_price"],
                    "outputTokenPrice": row["output_token_price"],
                    "currency": row["currency"],
                    "isActive": bool(row["is_active"]),
                    "lastTestStatus": bool(row.get("last_test_status")),
                    "lastTestedAt": row.get("last_tested_at"),
                    "lastTestError": row.get("last_test_error"),
                    "createdAt": row["created_at"],
                    "updatedAt": row["updated_at"]
                },
                "timestamp": now
            }

        return {
            "success": True,
            "message": "模型更新成功",
            "timestamp": now
        }

    except Exception as e:
        logger.error(f"更新模型失败: {e}")
        return {
            "success": False,
            "message": f"更新模型失败: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }


@api_handler(body=DeleteModelRequest)
async def delete_model(body: DeleteModelRequest) -> Dict[str, Any]:
    """删除模型配置

    @param body 要删除的模型 ID
    @returns 删除结果
    """
    try:
        db = get_db()

        # 验证模型是否存在
        results = db.execute_query(
            "SELECT id, name, is_active FROM llm_models WHERE id = ?",
            (body.model_id,)
        )

        if not results:
            return {
                "success": False,
                "message": f"模型不存在: {body.model_id}",
                "timestamp": datetime.now().isoformat()
            }

        model = results[0]

        was_active = bool(model["is_active"])

        # 删除模型（若为激活模型，则删除后将没有激活模型）
        db.execute_update(
            "DELETE FROM llm_models WHERE id = ?",
            (body.model_id,)
        )

        if was_active:
            logger.info(
                f"激活模型已删除并清空激活状态: {body.model_id} ({model['name']})"
            )
        else:
            logger.info(f"模型已删除: {body.model_id} ({model['name']})")

        return {
            "success": True,
            "message": f"模型已删除: {model['name']}",
            "data": {
                "modelId": body.model_id,
                "modelName": model["name"]
            },
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"删除模型失败: {e}")
        return {
            "success": False,
            "message": f"删除模型失败: {str(e)}",
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
                   is_active, last_test_status, last_tested_at, last_test_error,
                   created_at, updated_at
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
                "lastTestStatus": bool(row.get("last_test_status")),
                "lastTestedAt": row.get("last_tested_at"),
                "lastTestError": row.get("last_test_error"),
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
                "lastTestStatus": bool(row.get("last_test_status")),
                "lastTestedAt": row.get("last_tested_at"),
                "lastTestError": row.get("last_test_error"),
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
        db.execute_update(
            "UPDATE llm_models SET last_test_status = 0, last_tested_at = NULL, last_test_error = NULL WHERE id = ?",
            (body.model_id,)
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


@api_handler(body=TestModelRequest)
async def test_model(body: TestModelRequest) -> Dict[str, Any]:
    """测试指定模型的 API 连接是否可用"""

    db = get_db()
    model = db.get_llm_model_by_id(body.model_id)

    if not model:
        return {
            "success": False,
            "message": f"模型不存在: {body.model_id}",
            "timestamp": datetime.now().isoformat()
        }

    provider = (model.get("provider") or "").lower()
    api_url = (model.get("api_url") or "").strip()
    api_key = model.get("api_key") or ""

    if not api_url or not api_key:
        return {
            "success": False,
            "message": "模型配置缺少 API 地址或密钥，无法执行测试",
            "timestamp": datetime.now().isoformat()
        }

    base_url = api_url.rstrip("/")
    if base_url.endswith("/chat/completions") or base_url.endswith("/completions"):
        url = base_url
    else:
        url = f"{base_url}/chat/completions"

    headers = {"Content-Type": "application/json"}
    if provider == "anthropic":
        headers["x-api-key"] = api_key
        headers.setdefault("anthropic-version", "2023-06-01")
    else:
        headers["Authorization"] = f"Bearer {api_key}"

    # 构建最小化测试请求
    if provider == "anthropic":
        payload: Dict[str, Any] = {
            "model": model.get("model"),
            "max_tokens": 32,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Respond with OK"
                        }
                    ]
                }
            ]
        }
    else:
        payload = {
            "model": model.get("model"),
            "messages": [
                {
                    "role": "user",
                    "content": "Respond with OK"
                }
            ],
            "max_tokens": 16,
            "temperature": 0
        }

    success = False
    status_message = ""
    error_detail = None

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
            response = await client.post(url, headers=headers, json=payload)
        if 200 <= response.status_code < 400:
            success = True
            status_message = "模型 API 测试通过"
        else:
            error_detail = response.text[:500] if response.text else f"HTTP {response.status_code}"
            status_message = f"模型 API 测试失败: HTTP {response.status_code}"
    except Exception as exc:
        error_detail = str(exc)
        status_message = f"模型 API 测试异常: {exc.__class__.__name__}"

    # 更新数据库中的测试结果
    db.update_model_test_result(body.model_id, success, error_detail)

    tested_at = datetime.now().isoformat()
    runtime_message = None

    if bool(model.get("is_active")):
        coordinator = get_coordinator()
        if success:
            try:
                coordinator.last_error = None
                await start_runtime()
                runtime_message = "已尝试启动后台流程"
            except Exception as exc:
                runtime_message = f"后台启动失败: {exc}"
        else:
            try:
                await stop_runtime(quiet=True)
            except Exception as exc:
                logger.warning(f"停止后台流程失败: {exc}")
            coordinator.last_error = error_detail or status_message
            coordinator._set_state(mode="requires_model", error=coordinator.last_error)

    return {
        "success": success,
        "message": status_message,
        "data": {
            "modelId": model.get("id"),
            "provider": model.get("provider"),
            "testedAt": tested_at,
            "error": error_detail,
            "runtimeMessage": runtime_message
        },
        "timestamp": tested_at
    }
