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
from app.services.diagnosis.service import diagnose_shop_skus
from app.services.pdd.sync import PddSyncService


def _decode_stats(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        decoded = json.loads(value)
        return decoded if isinstance(decoded, dict) else {}
    except json.JSONDecodeError:
        return {}


def _result_has_changes(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in {
                "created",
                "updated",
                "orders",
                "refunds",
                "products_created",
                "products_updated",
                "skus_created",
                "skus_updated",
                "records_relinked",
            } and isinstance(nested, (int, float)) and nested > 0:
                return True
            if _result_has_changes(nested):
                return True
    elif isinstance(value, list):
        return any(_result_has_changes(item) for item in value)
    return False


class SyncRunner:
    def __init__(self, max_workers: int = 2) -> None:
        self.executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="pdd-sync"
        )
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

    def recover_stale_jobs(self) -> int:
        recovered = 0
        with session_scope() as session:
            jobs = session.scalars(
                select(SyncJob).where(SyncJob.status.in_(("queued", "running")))
            ).all()
            for job in jobs:
                stats = _decode_stats(job.stats_json)
                stats.update(
                    {
                        "stage": "interrupted",
                        "progress": stats.get("progress", 0),
                        "recoverable": True,
                    }
                )
                job.status = "failed"
                job.error_message = "上次程序退出时同步未完成，请点击重试"
                job.stats_json = json.dumps(stats, ensure_ascii=False, default=str)
                recovered += 1
        return recovered

    def submit(
        self,
        shop_id: int,
        job_type: str,
        *,
        retry_of: int | None = None,
        **kwargs: Any,
    ) -> int:
        with self._lock:
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
                        {
                            "stage": "queued",
                            "progress": 0,
                            "params": kwargs,
                            "retry_of": retry_of,
                        },
                        ensure_ascii=False,
                    ),
                )
                session.add(job)
                session.flush()
                job_id = job.id
        self.executor.submit(self._execute, job_id, shop_id, job_type, kwargs)
        return job_id

    def retry(self, job_id: int) -> int:
        with session_scope() as session:
            job = session.get(SyncJob, job_id)
            if job is None:
                raise LookupError("同步任务不存在")
            if job.status != "failed":
                raise ValueError("只有失败或中断的同步任务可以重试")
            stats = _decode_stats(job.stats_json)
            params = stats.get("params") if isinstance(stats.get("params"), dict) else {}
            shop_id = job.shop_id
            job_type = job.job_type
        return self.submit(
            shop_id,
            job_type,
            retry_of=job_id,
            **params,
        )

    def _merge_job_stats(self, job_id: int, **updates: Any) -> None:
        with session_scope() as session:
            job = session.get(SyncJob, job_id)
            if job is None:
                return
            stats = _decode_stats(job.stats_json)
            stats.update(updates)
            job.stats_json = json.dumps(stats, ensure_ascii=False, default=str)

    def _execute(
        self, job_id: int, shop_id: int, job_type: str, kwargs: dict[str, Any]
    ) -> None:
        with session_scope() as session:
            job = session.get(SyncJob, job_id)
            if job is None:
                return
            job.status = "running"
            stats = _decode_stats(job.stats_json)
            stats.update({"stage": "starting", "progress": 1})
            job.stats_json = json.dumps(stats, ensure_ascii=False)
            job.error_message = None

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

            diagnosis: dict[str, object] | None = None
            if job_type != "products" and _result_has_changes(result):
                self._merge_job_stats(job_id, stage="diagnosis", progress=92)
                diagnosis = diagnose_shop_skus(shop_id, limit=2000)

            with session_scope() as session:
                job = session.get(SyncJob, job_id)
                if job:
                    stats = _decode_stats(job.stats_json)
                    stats.update(
                        {
                            "stage": "completed",
                            "progress": 100,
                            "result": result,
                            "diagnosis": diagnosis,
                        }
                    )
                    job.status = "success"
                    job.stats_json = json.dumps(
                        stats, ensure_ascii=False, default=str
                    )
                    job.error_message = None
        except Exception as exc:
            with session_scope() as session:
                job = session.get(SyncJob, job_id)
                if job:
                    stats = _decode_stats(job.stats_json)
                    stats.update(
                        {
                            "stage": "failed",
                            "error": str(exc),
                            "recoverable": True,
                        }
                    )
                    job.status = "failed"
                    job.stats_json = json.dumps(stats, ensure_ascii=False)
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
