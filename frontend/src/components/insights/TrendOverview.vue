<script setup>
import TrendDelta from './TrendDelta.vue'

const props = defineProps({ data: { type: Object, default: null } })
const emit = defineEmits(['open-sku'])
const money = (value) => `¥${Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
</script>

<template>
  <section v-if="data" class="trend-overview">
    <div class="trend-summary-grid">
      <article class="stat-card"><span>已跟踪 SKU</span><strong>{{ data.summary?.tracked || 0 }}</strong><small>最近 14 日有指标</small></article>
      <article class="stat-card danger-soft"><span>7 日 GMV 下滑</span><strong>{{ data.summary?.down || 0 }}</strong><small>近 7 日 vs 前 7 日</small></article>
      <article class="stat-card success-soft"><span>7 日 GMV 增长</span><strong>{{ data.summary?.up || 0 }}</strong><small>变化幅度 ≥ 8%</small></article>
      <article class="stat-card"><span>趋势数据不足</span><strong>{{ data.summary?.unknown || 0 }}</strong><small>不会强行判断</small></article>
    </div>
    <article v-if="data.top_decliners?.length" class="card">
      <div class="card-heading"><div><p class="section-kicker">TREND PRIORITY</p><h3>近 7 日下滑最快</h3></div><span class="muted">截至 {{ data.latest_date }}</span></div>
      <div class="trend-decliner-list">
        <button v-for="item in data.top_decliners" :key="item.sku_id" class="trend-decliner-row" @click="emit('open-sku', item.sku_id)">
          <span class="peer-name"><strong>{{ item.product_title }}</strong><small>{{ item.sku_name }} · 数据覆盖 {{ item.recent_days }}/7 vs {{ item.prior_days }}/7 天</small></span>
          <span><strong>{{ money(item.recent_daily_gmv) }}/日</strong><TrendDelta :value="item.gmv_change" /></span>
        </button>
      </div>
    </article>
  </section>
</template>
