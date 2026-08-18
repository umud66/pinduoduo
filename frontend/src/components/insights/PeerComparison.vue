<script setup>
import TrendDelta from './TrendDelta.vue'

const props = defineProps({ comparison: { type: Object, default: () => ({}) } })
const money = (value) => `¥${Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
const percent = (value) => value === null || value === undefined ? '—' : `${(Number(value) * 100).toFixed(1)}%`
const concentrationLabel = (value) => ({ high: '高度集中', medium: '较集中', balanced: '较均衡', unknown: '数据不足' }[value] || '未知')
</script>

<template>
  <article class="card insight-card">
    <div class="card-heading">
      <div><p class="section-kicker">PEER COMPARISON</p><h3>同商品 SKU 横向比较</h3></div>
      <span class="status-pill neutral">{{ comparison.peer_count || 0 }} 个 SKU</span>
    </div>
    <template v-if="comparison.target">
      <div class="peer-highlight">
        <div><small>当前 SKU 排名</small><strong>#{{ comparison.target.rank }}</strong></div>
        <div><small>近 7 日 GMV</small><strong>{{ money(comparison.target.gmv) }}</strong></div>
        <div><small>商品 GMV 占比</small><strong>{{ percent(comparison.target.gmv_share) }}</strong></div>
        <div><small>相对其他 SKU 均值</small><TrendDelta :value="comparison.relative_to_peer_avg" /></div>
      </div>
      <div class="peer-concentration">
        <span>SKU 贡献结构：<strong>{{ concentrationLabel(comparison.concentration) }}</strong></span>
        <span v-if="comparison.gmv_concentration_hhi !== null && comparison.gmv_concentration_hhi !== undefined">HHI {{ comparison.gmv_concentration_hhi }}</span>
      </div>
      <div class="peer-list">
        <div v-for="peer in comparison.peers" :key="peer.sku_id" class="peer-row" :class="{ target: peer.is_target }">
          <span class="peer-rank">#{{ peer.rank }}</span>
          <span class="peer-name"><strong>{{ peer.sku_name }}</strong><small>{{ peer.days }} 个数据日</small></span>
          <span class="peer-share"><strong>{{ money(peer.gmv) }}</strong><small>{{ percent(peer.gmv_share) }}</small></span>
        </div>
      </div>
    </template>
    <div v-else class="empty-state compact">暂无同商品 SKU 可比较数据</div>
  </article>
</template>
