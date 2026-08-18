<script setup>
defineProps({ reviews: { type: Array, default: () => [] } })
const statusText = (value) => ({ pending: '等待数据', completed: '已复盘', insufficient_data: '数据不足', skipped: '已跳过' }[value] || value)
const outcomeText = (value) => ({ improved: '改善', worsened: '恶化', stable_or_mixed: '持平/混合', insufficient_data: '数据不足' }[value] || '—')
const delta = (value) => value === null || value === undefined ? '—' : `${value > 0 ? '+' : ''}${(Number(value) * 100).toFixed(1)}%`
</script>

<template>
  <div class="review-timeline">
    <div v-for="review in reviews" :key="review.id || review.window_days" class="review-step" :class="review.status">
      <div class="review-step-head"><strong>{{ review.window_days }} 天</strong><span>{{ statusText(review.status) }}</span></div>
      <small>目标日期 {{ review.due_date }}</small>
      <template v-if="review.result?.outcome">
        <b>{{ outcomeText(review.result.outcome) }}</b>
        <span v-if="review.result.effect_score !== null && review.result.effect_score !== undefined">综合变化 {{ delta(review.result.effect_score) }}</span>
        <span v-if="review.result.observed_days">{{ review.result.observed_days }} 个有效数据日</span>
      </template>
    </div>
  </div>
</template>
