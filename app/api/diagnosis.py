from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.db.database import session_scope
from app.db.models import DiagnosisResult, Product, Sku
from app.services.ai.gateway import AIGatewayError
from app.services.ai.service import AIProviderService
from app.services.diagnosis.service import build_ai_context, diagnose_latest_sku

router = APIRouter(tags=["diagnosis"])
ai_service = AIProviderService()


@router.post("/diagnosis/skus/{sku_id}")
def run_sku_diagnosis(sku_id: int) -> dict[str, object]:
    try:
        return diagnose_latest_sku(sku_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/diagnosis/shops/{shop_id}/run")
def run_shop_diagnosis(shop_id: int, limit: int = Query(default=300, ge=1, le=2000)) -> dict[str, object]:
    with session_scope() as session:
        sku_ids = session.scalars(
            select(Sku.id)
            .join(Product, Sku.product_id == Product.id)
            .where(Product.shop_id == shop_id)
            .order_by(Sku.id)
            .limit(limit)
        ).all()
    success = 0
    skipped = 0
    errors: list[dict[str, object]] = []
    for sku_id in sku_ids:
        try:
            diagnose_latest_sku(int(sku_id))
            success += 1
        except LookupError:
            skipped += 1
        except Exception as exc:
            errors.append({"sku_id": int(sku_id), "error": str(exc)})
    return {
        "ok": not errors,
        "total": len(sku_ids),
        "success": success,
        "skipped": skipped,
        "errors": errors[:20],
    }


@router.post("/diagnosis/{diagnosis_id}/ai")
def analyze_diagnosis_with_ai(
    diagnosis_id: int,
    provider_id: int = Query(gt=0),
) -> dict[str, object]:
    with session_scope() as session:
        diagnosis = session.get(DiagnosisResult, diagnosis_id)
        if diagnosis is None:
            raise HTTPException(status_code=404, detail="诊断记录不存在")
        diagnosis_payload = json.loads(diagnosis.diagnosis_json)

    try:
        provider, runtime = ai_service.get_runtime_provider(provider_id)
        if not provider.chat_model:
            raise AIGatewayError("该 AI Provider 尚未配置聊天模型")
        result = runtime.chat(
            model=provider.chat_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是拼多多电商运营顾问。必须基于系统给出的确定性诊断，不得改写数据。"
                        "输出中文，先给一句结论，再给最多 5 条按优先级排序的动作，每条包含动作、原因、验证指标。"
                    ),
                },
                {"role": "user", "content": build_ai_context(diagnosis_payload)},
            ],
            temperature=0.2,
        )
    except (LookupError, AIGatewayError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    stored = {"provider_id": provider_id, "model": provider.chat_model, "text": result.text}
    with session_scope() as session:
        diagnosis = session.get(DiagnosisResult, diagnosis_id)
        if diagnosis is not None:
            diagnosis.ai_analysis_json = json.dumps(stored, ensure_ascii=False)
    return stored
