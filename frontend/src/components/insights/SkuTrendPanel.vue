<script setup>
import MetricTrendChart from './MetricTrendChart.vue'
import TrendDelta from './TrendDelta.vue'

const props = defineProps({ insights: { type: Object, default: null } })
const money = (value) => value === null || value === undefined ? '—' : `¥${Number(value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
const number = (value) => value === null || value === undefined ? '—' : Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
const percent = (value) => value === null || value === undefined ? '—' : `${(Number(value) * 100).toFixed(1)}%`
const metricRows = [
  { key: 'gmv', label: 'GMV', format: money },
  { key: 'sales_qty', label: '销量', format: number },
  { key: 'ctr', label: 'CTR', format: percent },
  { key: 'cvr', label: 'CVR', format: percent },
  { key: 'refund_rate', label: '退款率', format: percent, inverse: true },
  { key: 'ad_roi', label: '推广 ROI', format: number },
]
const persistenceDays = (code) => props.insights?.persistence?.issues?.find((item) => item.code === code)?.consecutive_days || 0
</script>

<template>
  <section v-if="insights" class="insight-stack">
    <article class="card insight-card">
      <div class="card-heading">
        <div><p class="section-kicker">TREND INSIGHTS</p><h3>趋势与持续性</h3></div>
        <span class="status-pill neutral">{{ insights.data_quality?.metric_days || 0 }} 个数据日</span>
      </div>
      <div v-if="insights.summary?.length" class="insight-summary-list">
        <div v-for="line in insights.summary" :key="line" class="insight-summary-item">{{ line }}</div>
      </div>
      <div class="period-compare-grid">
        <div>
          <p class="section-kicker">TODAY VS 7D AVG</p>
          <div v-for="metric in metricRows" :key="`today-${metric.key}`" class="period-metric-row">
            <span>{{ metric.label }}</span>
            <strong>{{ metric.format(insights.window_comparison?.today_vs_7d?.[metric.key]?.current) }}</strong>
            <TrendDelta :value="insights.window_comparison?.today_vs_7d?.[metric.key]?.change" :inverse="metric.inverse" />
          </div>
        </div>
        <div>
          <p class="section-kicker">RECENT 7D VS PRIOR 7D</p>
          <div v-for="metric in metricRows" :key="`week-${metric.key}`" class="period-metric-row">
            <span>{{ metric.label }}</span>
            <strong>{{ metric.format(insights.window_comparison?.week_over_week?.[metric.key]?.current) }}</strong>
            <TrendDelta :value="insights.window_comparison?.week_over_week?.[metric.key]?.change" :inverse="metric.inverse" />
          </div>
        </div>
      </div>
    </article>

    <article class="card insight-card">
      <div class="card-heading">
        <div><p class="section-kicker">30 DAY TREND</p><h3>GMV 走势</h3></div>
        <TrendDelta :value="insights.trend_30d?.change" />
      </div>
      <MetricTrendChart :points="insights.trend_30d?.points || []" field="gmv" />
    </article>

    <article class="card insight-card">
      <div class="card-heading">
        <div><p class="section-kicker">PERSISTENCE</p><h3>当前异常持续时间</h3></div>
        <strong>{{ insights.persistence?.max_consecutive_days || 0 }} 天</strong>
      </div>
      <div v-if="insights.persistence?.issues?.length" class="persistence-list">
        <div v-for="item in insights.persistence.issues" :key="item.code" class="persistence-row">
          <span><strong>{{ item.code }}</strong><small v-if="item.since">自 {{ item.since }}</small></span>
          <strong>{{ persistenceDays(item.code) }} 天</strong>
        </div>
      </div>
      <p v-else class="helper-text">需要连续的历史诊断记录后才能判断异常持续时间；缺失日期不会被系统自动补齐。</p>
    </article>
  </section>
</template>
