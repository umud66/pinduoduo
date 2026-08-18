from __future__ import annotations

from html import escape
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.db.database import session_scope
from app.services.pdd.auth import PddAuthorizationService, authorization_payload

router = APIRouter(prefix="/pdd", tags=["pdd-auth"])
service = PddAuthorizationService()

class ApplicationUpdate(BaseModel):
    client_id: str = Field(min_length=1, max_length=128)
    client_secret: str | None = Field(default=None, max_length=512)
    redirect_uri: str = Field(min_length=1, max_length=2048)
    auth_web_url: str | None = Field(default=None, max_length=2048)

class CompleteAuthorization(BaseModel):
    state: str = Field(min_length=8, max_length=256)
    code: str = Field(min_length=1, max_length=2048)

@router.get("/application")
def get_application() -> dict[str, object]:
    with session_scope() as session:
        app = service.get_application(session)
        return authorization_payload(app, None)["application"] or {}

@router.put("/application")
def save_application(payload: ApplicationUpdate) -> dict[str, object]:
    try:
        with session_scope() as session:
            app = service.save_application(
                session,
                client_id=payload.client_id,
                client_secret=payload.client_secret,
                redirect_uri=payload.redirect_uri,
                auth_web_url=payload.auth_web_url,
            )
            return authorization_payload(app, None)["application"] or {}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.get("/shops/{shop_id}/authorization")
def get_authorization(shop_id: int) -> dict[str, object]:
    with session_scope() as session:
        app = service.get_application(session)
        auth = service.authorization(session, shop_id)
        return authorization_payload(app, auth)

@router.post("/shops/{shop_id}/authorization/start")
def start_authorization(shop_id: int) -> dict[str, object]:
    try:
        with session_scope() as session:
            app = service.get_application(session)
            flow, url = service.start(session, shop_id)
            return {
                "state": flow.state,
                "authorization_url": url,
                "redirect_uri": app.redirect_uri if app else None,
                "expires_at": flow.expires_at.isoformat(),
                "endpoint_status": app.endpoint_status if app else "unknown",
                "note": "授权地址/Token API 当前为 adapted，必须用真实开放平台应用继续验证。",
            }
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

@router.post("/authorization/complete")
def complete_authorization(payload: CompleteAuthorization) -> dict[str, object]:
    try:
        with session_scope() as session:
            auth = service.complete(session, state=payload.state, code=payload.code)
            app = service.get_application(session)
            return authorization_payload(app, auth)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"拼多多授权换 Token 失败：{exc}") from exc

@router.get("/oauth/callback", include_in_schema=False)
def oauth_callback(code: str = Query(min_length=1), state: str = Query(min_length=8)):
    try:
        with session_scope() as session:
            service.complete(session, state=state, code=code)
        return HTMLResponse("""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>授权成功</title>
<body style="font-family:sans-serif;padding:40px"><h2>拼多多店铺授权成功</h2>
<p>授权结果已保存到本机，可以关闭此窗口并返回运营助手。</p>
<script>try{window.opener&&window.opener.postMessage({type:'pdd-oauth-complete'},window.location.origin)}catch(e){}</script>
</body></html>""")
    except Exception as exc:
        return HTMLResponse(
            f"""<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>授权失败</title>
<body style="font-family:sans-serif;padding:40px"><h2>拼多多店铺授权未完成</h2>
<p>{escape(str(exc))}</p><p>返回运营助手重新发起授权，或使用开发模式手工提交 code。</p></body></html>""",
            status_code=400,
        )

@router.post("/shops/{shop_id}/authorization/refresh")
def refresh_authorization(shop_id: int) -> dict[str, object]:
    try:
        with session_scope() as session:
            auth = service.refresh(session, shop_id)
            app = service.get_application(session)
            return authorization_payload(app, auth)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"刷新拼多多授权失败：{exc}") from exc

@router.delete("/shops/{shop_id}/authorization")
def disconnect_authorization(shop_id: int) -> dict[str, bool]:
    with session_scope() as session:
        service.disconnect(session, shop_id)
        return {"ok": True}
