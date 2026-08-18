<script setup>
import TrendDelta from '@/components/insights/TrendDelta.vue'
defineProps({ data: { type: Object, default: null } })
const money = (value) => `¥${Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
</script>

<template>
  <article class="card decision-card">
    <div class="card-heading">
      <div><p class="section-kicker">CHANGE POINT</p><h3>经营变化点</h3></div>
      <span class="status-pill neutral">最近 {{ data?.data_days || 0 }} 个数据日</span>
    </div>
    <template v-if="data?.detected && data.primary">
      <div class="change-point-primary">
        <div><small>主要变化点</small><strong>{{ data.primary.date }}</strong></div>
        <div><small>变化前均值</small><strong>{{ money(data.primary.before_avg) }}</strong></div>
        <div><small>变化后均值</small><strong>{{ money(data.primary.after_avg) }}</strong></div>
        <div><small>变化幅度</small><TrendDelta :value="data.primary.change" /></div>
      </div>
      <div class="change-point-list">
        <div v-for="item in data.candidates" :key="`${item.date}-${item.direction}`" class="change-point-row">
          <span><strong>{{ item.date }}</strong><small>{{ item.recent ? '最近变化' : '历史变化' }} · 置信度 {{ Math.round(Number(item.confidence || 0) * 100) }}%</small></span>
          <TrendDelta :value="item.change" />
        </div>
      </div>
      <p class="helper-text">变化点用于提示“经营水平发生阶跃变化”的时间，不代表已经证明具体原因。</p>
    </template>
    <div v-else class="empty-state compact">当前真实数据点中未发现达到阈值的明显 GMV 水平变化。</div>
  </article>
</template>
