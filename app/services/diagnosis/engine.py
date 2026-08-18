from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from math import log
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
    ad_clicks: float | None = None
    ad_orders: float | None = None
    ad_gmv: float | None = None
    price: float | None = None

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

    @property
    def aov(self) -> float | None:
        if self.order_count <= 0:
            return None
        return self.gmv / self.order_count


@dataclass(slots=True)
class DiagnosisIssue:
    code: str
    category: str
    severity: str
    title: str
    reason: str
    evidence: dict[str, float | int | str | None]
    actions: list[str]
    validation_metrics: list[str]
    impact_score: int
    confidence: float
    priority_score: int
    estimated_loss: float = 0.0


@dataclass(slots=True)
class Diagnosis:
    health_score: int
    severity: str
    summary: str
    issues: list[DiagnosisIssue]
    decomposition: dict[str, object]
    data_quality: dict[str, object]

    def as_dict(self) -> dict[str, object]:
        return {
            "health_score": self.health_score,
            "severity": self.severity,
            "summary": self.summary,
            "issues": [asdict(issue) for issue in self.issues],
            "decomposition": self.decomposition,
            "data_quality": self.data_quality,
        }


def _change_ratio(current: float, baseline: float) -> float | None:
    if baseline <= 0:
        return None
    return (current - baseline) / baseline


def _confidence(sample: float, minimum: float, baseline_days: int, *, coverage: float = 1.0) -> float:
    sample_factor = min(1.0, max(0.0, sample / max(minimum, 1.0)))
    day_factor = min(1.0, max(0.25, baseline_days / 7))
    value = 0.40 + 0.35 * sample_factor + 0.20 * day_factor + 0.05 * max(0.0, min(1.0, coverage))
    return round(min(0.98, value), 2)


def _priority(impact_score: int, confidence: float) -> int:
    return max(0, min(100, round(impact_score * 0.68 + confidence * 100 * 0.32)))


def _severity(priority_score: int, *, forced_high: bool = False) -> str:
    if forced_high or priority_score >= 76:
        return "high"
    if priority_score >= 48:
        return "medium"
    return "low"


def _factor_attribution(current: MetricSnapshot, baseline: MetricSnapshot) -> dict[str, object]:
    baseline_gmv = max(0.0, baseline.gmv)
    current_gmv = max(0.0, current.gmv)
    drop_amount = max(0.0, baseline_gmv - current_gmv)
    gmv_change = _change_ratio(current_gmv, baseline_gmv)

    factors: list[dict[str, object]] = []
    mode = "unavailable"

    full = (
        current.impression is not None
        and baseline.impression is not None
        and current.ctr is not None
        and baseline.ctr is not None
        and current.cvr is not None
        and baseline.cvr is not None
        and current.aov is not None
        and baseline.aov is not None
        and baseline.impression > 0
        and baseline.ctr > 0
        and baseline.cvr > 0
        and baseline.aov > 0
    )
    if full:
        mode = "full_funnel"
        raw = [
            ("traffic", "曝光", current.impression, baseline.impression),
            ("click", "点击率", current.ctr, baseline.ctr),
            ("conversion", "转化率", current.cvr, baseline.cvr),
            ("aov", "客单价", current.aov, baseline.aov),
        ]
    elif (
        current.order_count >= 0
        and baseline.order_count > 0
        and current.aov is not None
        and baseline.aov is not None
        and baseline.aov > 0
    ):
        mode = "order_value"
        raw = [
            ("orders", "订单量", current.order_count, baseline.order_count),
            ("aov", "客单价", current.aov, baseline.aov),
        ]
    else:
        raw = []

    deteriorations: list[float] = []
    for _, _, current_value, baseline_value in raw:
        if current_value is None or baseline_value is None or baseline_value <= 0:
            deteriorations.append(0.0)
            continue
        ratio = max(float(current_value) / float(baseline_value), 1e-6)
        deteriorations.append(max(0.0, -log(ratio)))

    total_deterioration = sum(deteriorations)
    for index, (code, label, current_value, baseline_value) in enumerate(raw):
        change = (
            _change_ratio(float(current_value), float(baseline_value))
            if current_value is not None and baseline_value is not None
            else None
        )
        share = deteriorations[index] / total_deterioration if total_deterioration > 0 else 0.0
        estimated_loss = drop_amount * share
        factors.append(
            {
                "code": code,
                "label": label,
                "current": current_value,
                "baseline": baseline_value,
                "change": change,
                "loss_share": round(share, 4),
                "estimated_loss": round(estimated_loss, 2),
            }
        )

    factors.sort(key=lambda item: float(item["estimated_loss"]), reverse=True)
    return {
        "mode": mode,
        "baseline_gmv": round(baseline_gmv, 2),
        "current_gmv": round(current_gmv, 2),
        "gmv_change": gmv_change,
        "estimated_gmv_loss": round(drop_amount, 2),
        "factors": factors,
    }


def _data_quality(current: MetricSnapshot, baseline_days: int) -> dict[str, object]:
    fields = {
        "traffic": current.impression is not None,
        "click": current.clicks is not None,
        "conversion": current.clicks is not None,
        "inventory": current.stock is not None,
        "promotion": current.ad_cost is not None and current.ad_gmv is not None,
        "price": current.price is not None,
    }
    available = [name for name, present in fields.items() if present]
    missing = [name for name, present in fields.items() if not present]
    coverage_score = round(len(available) / len(fields) * 100)
    baseline_score = min(100, round(max(0, baseline_days) / 7 * 100))
    overall = round(coverage_score * 0.7 + baseline_score * 0.3)
    confidence = "high" if overall >= 80 else "medium" if overall >= 55 else "low"
    return {
        "coverage_score": coverage_score,
        "baseline_days": baseline_days,
        "baseline_score": baseline_score,
        "overall_score": overall,
        "confidence": confidence,
        "available": available,
        "missing": missing,
    }


def _loss_for_factor(decomposition: dict[str, object], factor_code: str) -> float:
    for factor in decomposition.get("factors", []):
        if isinstance(factor, dict) and factor.get("code") == factor_code:
            return float(factor.get("estimated_loss") or 0)
    return 0.0


def _append_issue(
    issues: list[DiagnosisIssue],
    *,
    code: str,
    category: str,
    title: str,
    reason: str,
    evidence: dict[str, float | int | str | None],
    actions: list[str],
    validation_metrics: list[str],
    impact_score: int,
    confidence: float,
    estimated_loss: float = 0.0,
    forced_high: bool = False,
) -> None:
    priority = _priority(impact_score, confidence)
    issues.append(
        DiagnosisIssue(
            code=code,
            category=category,
            severity=_severity(priority, forced_high=forced_high),
            title=title,
            reason=reason,
            evidence=evidence,
            actions=actions,
            validation_metrics=validation_metrics,
            impact_score=max(0, min(100, impact_score)),
            confidence=confidence,
            priority_score=priority,
            estimated_loss=round(max(0.0, estimated_loss), 2),
        )
    )


def diagnose(
    current: MetricSnapshot,
    baseline: MetricSnapshot,
    *,
    baseline_days: int = 7,
) -> Diagnosis:
    issues: list[DiagnosisIssue] = []
    decomposition = _factor_attribution(current, baseline)
    quality = _data_quality(current, baseline_days)

    sales_change = _change_ratio(current.sales_qty, baseline.sales_qty)
    traffic_change = (
        _change_ratio(current.impression, baseline.impression)
        if current.impression is not None and baseline.impression is not None
        else None
    )
    ctr_change = (
        _change_ratio(current.ctr, baseline.ctr)
        if current.ctr is not None and baseline.ctr is not None
        else None
    )
    cvr_change = (
        _change_ratio(current.cvr, baseline.cvr)
        if current.cvr is not None and baseline.cvr is not None
        else None
    )
    aov_change = (
        _change_ratio(current.aov, baseline.aov)
        if current.aov is not None and baseline.aov is not None
        else None
    )

    root_cause_count = 0

    if (
        baseline.impression is not None
        and baseline.impression >= 300
        and current.impression is not None
        and traffic_change is not None
        and traffic_change <= -0.25
    ):
        impact = min(100, round(45 + abs(traffic_change) * 85))
        confidence = _confidence(max(current.impression, baseline.impression), 300, baseline_days)
        _append_issue(
            issues,
            code="TRAFFIC_DROP",
            category="traffic",
            title="曝光流量明显下降",
            reason="曝光量相对近期基线显著减少，会直接压缩后续点击和成交上限。",
            evidence={
                "current_impression": current.impression,
                "baseline_impression": baseline.impression,
                "change": traffic_change,
            },
            actions=[
                "先检查商品是否降权、下架、活动退出或搜索/推荐入口发生变化",
                "对照近 7 日流量来源，找出下降最明显的入口",
                "确认价格、标题、类目属性近期是否有影响分发的改动",
            ],
            validation_metrics=["曝光量恢复幅度", "流量来源占比", "GMV 恢复幅度"],
            impact_score=impact,
            confidence=confidence,
            estimated_loss=_loss_for_factor(decomposition, "traffic"),
        )
        root_cause_count += 1

    if (
        current.impression is not None
        and current.impression >= 100
        and baseline.ctr is not None
        and ctr_change is not None
        and ctr_change <= -0.25
    ):
        impact = min(100, round(44 + abs(ctr_change) * 90))
        confidence = _confidence(current.impression, 100, baseline_days)
        _append_issue(
            issues,
            code="CTR_DROP",
            category="click",
            title="点击率下降",
            reason="商品仍有一定曝光，但点击承接弱于近期基线，优先检查主图、价格展示和首屏卖点。",
            evidence={
                "current_ctr": current.ctr,
                "baseline_ctr": baseline.ctr,
                "change": ctr_change,
                "impression": current.impression,
            },
            actions=[
                "保留当前主图作为对照，新增 1~2 个明确卖点版本做小流量测试",
                "检查到手价、优惠标签和同款价格竞争力",
                "主图一次只调整一个主要变量，避免无法判断提升来源",
            ],
            validation_metrics=["CTR", "点击量", "每千次曝光成交额"],
            impact_score=impact,
            confidence=confidence,
            estimated_loss=_loss_for_factor(decomposition, "click"),
        )
        root_cause_count += 1

    if (
        current.clicks is not None
        and current.clicks >= 20
        and baseline.cvr is not None
        and cvr_change is not None
        and cvr_change <= -0.25
    ):
        impact = min(100, round(46 + abs(cvr_change) * 92))
        confidence = _confidence(current.clicks, 20, baseline_days)
        _append_issue(
            issues,
            code="CVR_DROP",
            category="conversion",
            title="支付转化率下降",
            reason="点击量具备一定样本，但订单转化明显低于近期水平，问题更可能发生在价格、SKU、详情或信任承接环节。",
            evidence={
                "current_cvr": current.cvr,
                "baseline_cvr": baseline.cvr,
                "change": cvr_change,
                "clicks": current.clicks,
            },
            actions=[
                "检查主销 SKU 是否缺货、涨价或优惠减少",
                "对照近期差评/退款原因，检查详情描述和实物预期差异",
                "检查价格梯度，避免低价引流规格无货导致有效点击浪费",
            ],
            validation_metrics=["CVR", "订单数", "主销 SKU 库存", "加购到支付转化"],
            impact_score=impact,
            confidence=confidence,
            estimated_loss=_loss_for_factor(decomposition, "conversion"),
        )
        root_cause_count += 1

    if (
        current.order_count >= 5
        and baseline.order_count >= 5
        and aov_change is not None
        and aov_change <= -0.15
    ):
        impact = min(86, round(35 + abs(aov_change) * 100))
        confidence = _confidence(current.order_count, 5, baseline_days)
        _append_issue(
            issues,
            code="AOV_DROP",
            category="price_mix",
            title="成交客单价下降",
            reason="订单量已有样本，但每单成交金额下降，可能来自价格变化、优惠加深或成交 SKU 结构下沉。",
            evidence={
                "current_aov": current.aov,
                "baseline_aov": baseline.aov,
                "change": aov_change,
                "current_price": current.price,
                "baseline_price": baseline.price,
            },
            actions=[
                "检查近期改价、优惠券和活动折扣是否压低真实成交价",
                "比较不同 SKU 的订单占比，确认是否由低价规格占比上升导致",
                "在不影响转化的前提下测试组合装或高价值规格承接",
            ],
            validation_metrics=["客单价", "GMV", "各 SKU 成交占比", "CVR"],
            impact_score=impact,
            confidence=confidence,
            estimated_loss=_loss_for_factor(decomposition, "aov"),
        )
        root_cause_count += 1

    price_change = (
        _change_ratio(current.price, baseline.price)
        if current.price is not None and baseline.price is not None
        else None
    )
    if (
        price_change is not None
        and abs(price_change) >= 0.10
        and sales_change is not None
        and sales_change <= -0.20
    ):
        impact = min(84, round(42 + abs(sales_change) * 55 + abs(price_change) * 30))
        confidence = _confidence(max(current.order_count, current.sales_qty), 5, baseline_days, coverage=0.9)
        direction = "上涨" if price_change > 0 else "下降"
        _append_issue(
            issues,
            code="PRICE_CHANGE_SALES_DROP",
            category="price",
            title=f"价格{direction}后销量走弱",
            reason="价格相对基线发生明显变化，同时销量下降，价格变化与掉量具有较强时间共现，需要优先验证因果关系。",
            evidence={
                "current_price": current.price,
                "baseline_price": baseline.price,
                "price_change": price_change,
                "sales_change": sales_change,
            },
            actions=[
                "核对活动价、券后价和竞品到手价，确认用户实际看到的价格差",
                "不要直接大幅改价，优先用小幅价格/优惠测试验证价格弹性",
            ],
            validation_metrics=["销量", "CVR", "GMV", "价格调整前后 3~7 日表现"],
            impact_score=impact,
            confidence=confidence,
        )
        root_cause_count += 1

    if current.refund_rate is not None and current.order_count >= 5:
        baseline_refund = baseline.refund_rate or 0
        high_vs_baseline = baseline_refund > 0 and current.refund_rate >= baseline_refund * 1.5
        if current.refund_rate >= 0.10 or high_vs_baseline:
            excess = max(0.0, current.refund_rate - baseline_refund)
            impact = min(100, round(48 + current.refund_rate * 140 + excess * 90))
            confidence = _confidence(current.order_count, 5, baseline_days)
            _append_issue(
                issues,
                code="REFUND_HIGH",
                category="after_sales",
                title="退款率异常",
                reason="退款率达到高风险水平或显著高于近期基线，会直接侵蚀有效 GMV，并可能影响后续商品表现。",
                evidence={
                    "current_refund_rate": current.refund_rate,
                    "baseline_refund_rate": baseline.refund_rate,
                    "refund_count": current.refund_count,
                    "order_count": current.order_count,
                },
                actions=[
                    "按退款原因聚类，优先排查质量、描述不符、尺寸/规格和物流问题",
                    "对异常 SKU 暂缓扩大推广，先定位退款集中批次或规格",
                    "把高频退款原因改写成详情页明确说明，降低预期偏差",
                ],
                validation_metrics=["退款率", "退款原因分布", "净 GMV", "差评率"],
                impact_score=impact,
                confidence=confidence,
                forced_high=current.refund_rate >= 0.20,
            )
            root_cause_count += 1

    if current.stock is not None and current.sales_qty > 0:
        sellable_days = current.stock / current.sales_qty
        if sellable_days < 3:
            impact = min(100, round(64 + max(0.0, 3 - sellable_days) * 12))
            confidence = _confidence(current.sales_qty, 3, baseline_days)
            _append_issue(
                issues,
                code="STOCK_RISK",
                category="inventory",
                title="可售库存偏低",
                reason="按当前销量估算的可售天数过低，存在断货、排名和推广流量损失风险。",
                evidence={
                    "stock": current.stock,
                    "sales_qty": current.sales_qty,
                    "sellable_days": sellable_days,
                },
                actions=[
                    "优先补充该规格库存并确认实际可发库存",
                    "补货前避免继续放大推广预算",
                    "如无法及时补货，提前把流量引导到可替代规格",
                ],
                validation_metrics=["可售天数", "缺货率", "销量", "主销 SKU 库存"],
                impact_score=impact,
                confidence=confidence,
            )
            root_cause_count += 1
        elif sellable_days >= 60 and current.stock >= 30 and baseline.sales_qty >= 1:
            impact = min(72, round(34 + min(30, (sellable_days - 60) * 0.35)))
            confidence = _confidence(baseline.sales_qty, 1, baseline_days, coverage=0.8)
            _append_issue(
                issues,
                code="STOCK_EXCESS",
                category="inventory",
                title="库存周转偏慢",
                reason="按当前销量估算库存覆盖周期过长，存在资金占用和后续清仓压力。",
                evidence={
                    "stock": current.stock,
                    "sales_qty": current.sales_qty,
                    "sellable_days": sellable_days,
                },
                actions=[
                    "暂停继续补货，先确认现有库存真实可售数量",
                    "结合毛利评估是否需要组合装、搭售或定向促销",
                ],
                validation_metrics=["库存周转天数", "销量", "毛利额"],
                impact_score=impact,
                confidence=confidence,
            )
            root_cause_count += 1

    if current.ad_roi is not None and current.ad_cost is not None and current.ad_cost >= 10:
        roi_change = (
            _change_ratio(current.ad_roi, baseline.ad_roi)
            if baseline.ad_roi is not None
            else None
        )
        if current.ad_roi < 1 or (roi_change is not None and roi_change <= -0.30):
            impact = min(100, round(55 + max(0.0, 1 - current.ad_roi) * 35 + abs(min(0.0, roi_change or 0)) * 45))
            confidence = _confidence(current.ad_cost, 20, baseline_days)
            _append_issue(
                issues,
                code="AD_ROI_LOW",
                category="promotion",
                title="推广投产偏低",
                reason="当前推广消耗已有一定规模，但推广成交产出不足或较近期明显恶化。",
                evidence={
                    "ad_cost": current.ad_cost,
                    "current_roi": current.ad_roi,
                    "baseline_roi": baseline.ad_roi,
                    "change": roi_change,
                },
                actions=[
                    "先拆出高消耗低成交计划/单元，设置止损线",
                    "结合 CTR/CVR 判断是素材点击问题还是商品承接问题",
                    "缩量时保留能稳定成交的计划，避免整体一刀切",
                ],
                validation_metrics=["推广 ROI", "推广成交额", "推广花费", "整体 GMV"],
                impact_score=impact,
                confidence=confidence,
                forced_high=current.ad_roi < 0.7,
            )
            root_cause_count += 1

    if (
        baseline.sales_qty >= 3
        and sales_change is not None
        and sales_change <= -0.30
    ):
        impact = min(78, round((20 if root_cause_count else 48) + abs(sales_change) * (50 if root_cause_count else 65)))
        confidence = _confidence(
            max(current.sales_qty, baseline.sales_qty),
            3,
            baseline_days,
            coverage=quality["coverage_score"] / 100,
        )
        located = root_cause_count > 0
        _append_issue(
            issues,
            code="SALES_DROP",
            category="sales",
            title="销量明显下降" if located else "销量明显下降，但数据不足以定位环节",
            reason=(
                "销量下降是当前结果指标；系统已识别更具体的上游问题，应优先处理优先级更高的根因项。"
                if located
                else "销量下降已经成立，但当前可用数据没有足够证据区分流量、点击、转化或其他原因。"
            ),
            evidence={
                "current": current.sales_qty,
                "baseline": baseline.sales_qty,
                "change": sales_change,
            },
            actions=(
                ["优先处理列表中 priority_score 更高的根因项", "根因调整后观察销量和 GMV 是否同步恢复"]
                if located
                else ["优先补充曝光、点击、访客和推广报表，再进行漏斗定位", "同时检查商品状态、价格、库存和近期活动变化"]
            ),
            validation_metrics=["销量", "GMV", "曝光", "CTR", "CVR"],
            impact_score=impact,
            confidence=confidence,
            estimated_loss=float(decomposition.get("estimated_gmv_loss") or 0),
        )

    issues.sort(key=lambda item: (-item.priority_score, -item.impact_score, item.code))

    penalty = 0.0
    for index, issue in enumerate(issues):
        diminishing = 1.0 if index == 0 else 0.65 if index == 1 else 0.4
        penalty += (7 + issue.priority_score * 0.16) * diminishing
    health_score = max(0, min(100, round(100 - min(82, penalty))))

    severity = "healthy"
    if issues:
        top_priority = issues[0].priority_score
        severity = "high" if top_priority >= 76 else "medium" if top_priority >= 48 else "low"

    gmv_change = decomposition.get("gmv_change")
    if issues:
        top = issues[0]
        if isinstance(gmv_change, (int, float)) and gmv_change < 0:
            summary = (
                f"GMV 较近期基线下降 {abs(gmv_change) * 100:.1f}%，"
                f"当前优先处理“{top.title}”，诊断置信度 {top.confidence * 100:.0f}%。"
            )
        else:
            summary = f"当前优先处理“{top.title}”，诊断置信度 {top.confidence * 100:.0f}%。"
    else:
        summary = "当前样本下未发现达到规则阈值的明显经营异常。"

    return Diagnosis(
        health_score=health_score,
        severity=severity,
        summary=summary,
        issues=issues,
        decomposition=decomposition,
        data_quality=quality,
    )


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
        ad_clicks=avg("ad_clicks", nullable=True),
        ad_orders=avg("ad_orders", nullable=True),
        ad_gmv=avg("ad_gmv", nullable=True),
        price=avg("price", nullable=True),
    )


def snapshot_payload(snapshot: MetricSnapshot) -> dict[str, float | None]:
    return {
        "sales_qty": snapshot.sales_qty,
        "order_count": snapshot.order_count,
        "gmv": snapshot.gmv,
        "refund_count": snapshot.refund_count,
        "refund_amount": snapshot.refund_amount,
        "impression": snapshot.impression,
        "clicks": snapshot.clicks,
        "visitors": snapshot.visitors,
        "stock": snapshot.stock,
        "ad_cost": snapshot.ad_cost,
        "ad_clicks": snapshot.ad_clicks,
        "ad_orders": snapshot.ad_orders,
        "ad_gmv": snapshot.ad_gmv,
        "price": snapshot.price,
        "ctr": snapshot.ctr,
        "cvr": snapshot.cvr,
        "refund_rate": snapshot.refund_rate,
        "ad_roi": snapshot.ad_roi,
        "aov": snapshot.aov,
    }


def number(value: Decimal | int | float | None) -> float | None:
    return None if value is None else float(value)
