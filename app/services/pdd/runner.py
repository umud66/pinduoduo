from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select

from app.db.database import session_scope
from app.db.models import Shop, SyncJob
from app.db.sync_models import SyncPreference
from app.services.pdd.sync import PddSyncService


class SyncRunner:
    def __init__(self, max_workers: int = 2) -> None:
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="pdd-sync")
        self._lock = threading.Lock()

    def has_active_job(self, shop_id: int) -> bool:
        with session_scope() as session:
            active = session.scalar(
                select(SyncJob.id)
                .where(
                    SyncJob.shop_id == shop_id,
                    SyncJob.status.in_(("queued", "running")),
                )
                .limit(1)
            )
            return active is not None

    def submit(self, shop_id: int, job_type: str, **kwargs: Any) -> int:
        if self.has_active_job(shop_id):
            raise RuntimeError("该店铺已有同步任务正在运行")
        with session_scope() as session:
            if session.get(Shop, shop_id) is None:
                raise LookupError("店铺不存在")
            job = SyncJob(
                shop_id=shop_id,
                job_type=job_type,
                status="queued",
                stats_json=json.dumps(
                    {"stage": "queued", "progress": 0}, ensure_ascii=False
                ),
            )
            session.add(job)
            session.flush()
            job_id = job.id
        self.executor.submit(self._execute, job_id, shop_id, job_type, kwargs)
        return job_id

    def _execute(
        self, job_id: int, shop_id: int, job_type: str, kwargs: dict[str, Any]
    ) -> None:
        with session_scope() as session:
            job = session.get(SyncJob, job_id)
            if job is None:
                return
            job.status = "running"
            job.stats_json = json.dumps(
                {"stage": "starting", "progress": 1}, ensure_ascii=False
            )

        service = PddSyncService(shop_id)
        try:
            if job_type == "full":
                result = service.sync_full(
                    job_id, lookback_days=int(kwargs.get("lookback_days", 30))
                )
            elif job_type == "products":
                result = service.sync_products(job_id)
            elif job_type == "orders":
                result = service.sync_incremental_orders(
                    job_id, lookback_days=int(kwargs.get("lookback_days", 7))
                )
            elif job_type == "refunds":
                result = service.sync_refunds(
                    job_id, lookback_days=int(kwargs.get("lookback_days", 7))
                )
            elif job_type == "incremental":
                result = service.sync_incremental(job_id)
            else:
                raise ValueError(f"未知同步类型: {job_type}")

            with session_scope() as session:
                job = session.get(SyncJob, job_id)
                if job:
                    job.status = "success"
                    job.stats_json = json.dumps(
                        {
                            "stage": "completed",
                            "progress": 100,
                            "result": result,
                        },
                        ensure_ascii=False,
                        default=str,
                    )
        except Exception as exc:
            with session_scope() as session:
                job = session.get(SyncJob, job_id)
                if job:
                    job.status = "failed"
                    current: dict[str, Any] = {}
                    try:
                        current = json.loads(job.stats_json or "{}")
                    except json.JSONDecodeError:
                        current = {}
                    current.update({"stage": "failed", "error": str(exc)})
                    job.stats_json = json.dumps(current, ensure_ascii=False)
                    job.error_message = str(exc)

    def shutdown(self) -> None:
        self.executor.shutdown(wait=False, cancel_futures=False)


sync_runner = SyncRunner()


class AutoSyncScheduler:
    def __init__(self, poll_seconds: int = 60) -> None:
        self.poll_seconds = poll_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="pdd-auto-sync", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _loop(self) -> None:
        while not self._stop.wait(self.poll_seconds):
            try:
                self._tick()
            except Exception:
                continue

    def _tick(self) -> None:
        now = datetime.utcnow()
        due_shop_ids: list[int] = []
        with session_scope() as session:
            prefs = session.scalars(
                select(SyncPreference).where(SyncPreference.auto_sync.is_(True))
            ).all()
            for pref in prefs:
                interval = max(15, pref.interval_minutes or 30)
                due_at = (
                    pref.last_auto_sync_at + timedelta(minutes=interval)
                    if pref.last_auto_sync_at
                    else None
                )
                if due_at is None or due_at <= now:
                    due_shop_ids.append(pref.shop_id)

        for shop_id in due_shop_ids:
            if sync_runner.has_active_job(shop_id):
                continue
            try:
                sync_runner.submit(shop_id, "incremental")
            except (LookupError, RuntimeError):
                continue
            with session_scope() as session:
                pref = session.scalar(
                    select(SyncPreference).where(SyncPreference.shop_id == shop_id)
                )
                if pref:
                    pref.last_auto_sync_at = now


auto_sync_scheduler = AutoSyncScheduler()
