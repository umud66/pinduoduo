from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from statistics import mean
from typing import Iterable


@dataclass(slots=True)
class MetricSnapshot:
    sales_qty: float = 0
    order_count: float = 0
    gmv: float = 0
    refund_count: float = 0
    refund_amount: float = 0
    impression: float | None = None
    clicks: float | None = None
    visitors: float | None = None
    stock: float | None = None
    ad_cost: float | None = None
    ad_gmv: float | None = None

    @property
    def ctr(self) -> float | None:
        if self.impression is None or self.clicks is None or self.impression <= 0:
            return None
        return self.clicks / self.impression

    @property
    def cvr(self) -> float | None:
        if self.clicks is None or self.clicks <= 0:
            return None
        return self.order_count / self.clicks

    @property
    def refund_rate(self) -> float | None:
        if self.order_count <= 0:
            return None
        return self.refund_count / self.order_count

    @property
    def ad_roi(self) -> float | None:
        if self.ad_cost is None or self.ad_gmv is None or self.ad_cost <= 0:
            return None
        return self.ad_gmv / self.ad_cost


@dataclass(slots=True)
class DiagnosisIssue:
    code: str
    category: str
    severity: str
    title: str
    evidence: dict[str, float | int | str | None]
    actions: list[str]


@dataclass(slots=True)
class Diagnosis:
    health_score: int
    severity: str
    issues: list[DiagnosisIssue]

    def as_dict(self) -> dict[str, object]:
        return {
            "health_score": self.health_score,
            "severity": self.severity,
            "issues": [asdict(issue) for issue in self.issues],
        }


def _drop_ratio(current: float, baseline: float) -> float | None:
    if baseline <= 0:
        return None
    return (current - baseline) / baseline


def _append_issue(
    issues: list[DiagnosisIssue],
    *,
    code: str,
    category: str,
    severity: str,
    title: str,
    evidence: dict[str, float | int | str | None],
    actions: list[str],
) -> None:
    issues.append(
        DiagnosisIssue(
            code=code,
            category=category,
            severity=severity,
            title=title,
            evidence=evidence,
            actions=actions,
        )
    )


def diagnose(current: MetricSnapshot, baseline: MetricSnapshot) -> Diagnosis:
    issues: list[DiagnosisIssue] = []

    sales_change = _drop_ratio(current.sales_qty, baseline.sales_qty)
    if baseline.sales_qty >= 3 and sales_change is not None and sales_change <= -0.30:
        _append_issue(
            issues,
            code="SALES_DROP",
            category="sales",
            severity="high" if sales_change <= -0.50 else "medium",
            title="销量明显下降",
            evidence={"current": current.sales_qty, "baseline": baseline.sales_qty, "change": sales_change},
            actions=["继续拆解曝光、点击、转化定位掉量环节", "检查价格、库存和商品状态是否发生变化"],
        )

    ctr_change = None
    if current.ctr is not None and baseline.ctr is not None:
        ctr_change = _drop_ratio(current.ctr, baseline.ctr)
    if (
        current.impression is not None
        and current.impression >= 100
        and ctr_change is not None
        and ctr_change <= -0.25
    ):
        _append_issue(
            issues,
            code="CTR_DROP",
            category="click",
            severity="high" if ctr_change <= -0.40 else "medium",
            title="点击率下降",
            evidence={"current_ctr": current.ctr, "baseline_ctr": baseline.ctr, "change": ctr_change},
            actions=["优先测试主图卖点和首屏信息", "检查到手价展示及同款价格竞争力", "保留旧图做 A/B 对照"],
        )

    cvr_change = None
    if current.cvr is not None and baseline.cvr is not None:
        cvr_change = _drop_ratio(current.cvr, baseline.cvr)
    if current.clicks is not None and current.clicks >= 20 and cvr_change is not None and cvr_change <= -0.25:
        _append_issue(
            issues,
            code="CVR_DROP",
            category="conversion",
            severity="high" if cvr_change <= -0.40 else "medium",
            title="支付转化率下降",
            evidence={"current_cvr": current.cvr, "baseline_cvr": baseline.cvr, "change": cvr_change},
            actions=["检查 SKU 价格梯度和优惠变化", "检查详情承接、评价和售后反馈", "确认高销量规格是否缺货"],
        )

    if current.refund_rate is not None and current.order_count >= 5:
        base_refund = baseline.refund_rate or 0
        high_vs_baseline = base_refund > 0 and current.refund_rate >= base_refund * 1.5
        if current.refund_rate >= 0.10 or high_vs_baseline:
            _append_issue(
                issues,
                code="REFUND_HIGH",
                category="after_sales",
                severity="high" if current.refund_rate >= 0.20 else "medium",
                title="退款率异常",
                evidence={"current_refund_rate": current.refund_rate, "baseline_refund_rate": baseline.refund_rate},
                actions=["按退款原因聚类检查质量、描述不符和尺寸问题", "暂停扩大异常 SKU 的推广", "核对批次和供应链变化"],
            )

    if current.stock is not None and current.sales_qty > 0:
        sellable_days = current.stock / current.sales_qty
        if sellable_days < 3:
            _append_issue(
                issues,
                code="STOCK_RISK",
                category="inventory",
                severity="high" if sellable_days < 1 else "medium",
                title="可售库存偏低",
                evidence={"stock": current.stock, "sales_qty": current.sales_qty, "sellable_days": sellable_days},
                actions=["优先补充该规格库存", "避免在补货前继续放大推广导致断货"],
            )

    if current.ad_roi is not None:
        roi_change = _drop_ratio(current.ad_roi, baseline.ad_roi) if baseline.ad_roi is not None else None
        if current.ad_roi < 1 or (roi_change is not None and roi_change <= -0.30):
            _append_issue(
                issues,
                code="AD_ROI_LOW",
                category="promotion",
                severity="high" if current.ad_roi < 0.8 else "medium",
                title="推广投产偏低",
                evidence={"current_roi": current.ad_roi, "baseline_roi": baseline.ad_roi, "change": roi_change},
                actions=["拆分计划检查高消耗低成交单元", "结合自然转化确认是否为商品承接问题", "设定止损阈值避免持续无效消耗"],
            )

    weights = {"high": 22, "medium": 12, "low": 5}
    health_score = max(0, 100 - sum(weights.get(issue.severity, 5) for issue in issues))
    severity = "healthy"
    if any(issue.severity == "high" for issue in issues):
        severity = "high"
    elif any(issue.severity == "medium" for issue in issues):
        severity = "medium"
    elif issues:
        severity = "low"
    return Diagnosis(health_score=health_score, severity=severity, issues=issues)


def average_snapshots(snapshots: Iterable[MetricSnapshot]) -> MetricSnapshot:
    items = list(snapshots)
    if not items:
        return MetricSnapshot()

    def avg(name: str, *, nullable: bool = False) -> float | None:
        values = [getattr(item, name) for item in items if getattr(item, name) is not None]
        if not values:
            return None if nullable else 0.0
        return float(mean(float(v) for v in values))

    return MetricSnapshot(
        sales_qty=float(avg("sales_qty") or 0),
        order_count=float(avg("order_count") or 0),
        gmv=float(avg("gmv") or 0),
        refund_count=float(avg("refund_count") or 0),
        refund_amount=float(avg("refund_amount") or 0),
        impression=avg("impression", nullable=True),
        clicks=avg("clicks", nullable=True),
        visitors=avg("visitors", nullable=True),
        stock=avg("stock", nullable=True),
        ad_cost=avg("ad_cost", nullable=True),
        ad_gmv=avg("ad_gmv", nullable=True),
    )


def number(value: Decimal | int | float | None) -> float | None:
    return None if value is None else float(value)
