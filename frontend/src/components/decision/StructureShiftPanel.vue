<script setup>
import TrendDelta from '@/components/insights/TrendDelta.vue'
defineProps({ data: { type: Object, default: null } })
const money = (value) => `¥${Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
const percent = (value) => value === null || value === undefined ? '—' : `${(Number(value) * 100).toFixed(1)}%`
const roleLabel = (value) => ({ loser: '份额流出候选', winner: '份额承接候选', neutral: '未发现明显迁移' }[value] || '数据不足')
</script>

<template>
  <article class="card decision-card">
    <div class="card-heading">
      <div><p class="section-kicker">SKU STRUCTURE SHIFT</p><h3>商品内规格结构变化</h3></div>
      <span class="status-pill" :class="data?.role === 'loser' ? 'medium' : 'neutral'">{{ roleLabel(data?.role) }}</span>
    </div>
    <div class="structure-summary">
      <div><small>商品近 7 日 GMV</small><strong>{{ money(data?.product_recent_gmv) }}</strong></div>
      <div><small>商品整体变化</small><TrendDelta :value="data?.product_gmv_change" /></div>
      <div><small>HHI 变化</small><strong>{{ data?.hhi_change === null || data?.hhi_change === undefined ? '—' : Number(data.hhi_change).toFixed(3) }}</strong></div>
      <div><small>参与 SKU</small><strong>{{ data?.peer_count || 0 }}</strong></div>
    </div>
    <div v-if="data?.primary_pair" class="structure-transfer">
      <div class="structure-flow">
        <span><small>份额流出</small><strong>{{ data.primary_pair.loser_name }}</strong></span>
        <span class="structure-arrow">→</span>
        <span><small>份额承接</small><strong>{{ data.primary_pair.winner_name }}</strong></span>
      </div>
      <div class="structure-transfer-meta">
        <span>估算迁移 {{ money(data.primary_pair.estimated_transfer) }}</span>
        <span>覆盖损失 {{ percent(data.primary_pair.transfer_ratio) }}</span>
        <span>置信度 {{ Math.round(Number(data.primary_pair.confidence || 0) * 100) }}%</span>
      </div>
      <p class="helper-text">只有“一个规格明显下降、另一个明显增长、商品整体 GMV 基本稳定”时才标记为蚕食/份额迁移候选；这是经营相关性，不是因果证明。</p>
    </div>
    <div v-else class="empty-state compact">当前没有满足保守条件的商品内 SKU 份额迁移候选。</div>
  </article>
</template>
