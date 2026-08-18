<script setup>
import { computed } from 'vue'

const props = defineProps({
  points: { type: Array, default: () => [] },
  field: { type: String, default: 'gmv' },
  height: { type: Number, default: 150 },
})

const width = 560
const padding = 14
const values = computed(() => props.points.map((item) => Number(item?.[props.field] || 0)))
const polyline = computed(() => {
  if (!values.value.length) return ''
  const min = Math.min(...values.value)
  const max = Math.max(...values.value)
  const range = Math.max(max - min, 1)
  return values.value.map((value, index) => {
    const x = values.value.length === 1 ? width / 2 : padding + index * ((width - padding * 2) / (values.value.length - 1))
    const y = props.height - padding - ((value - min) / range) * (props.height - padding * 2)
    return `${x.toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
})
const maxValue = computed(() => values.value.length ? Math.max(...values.value) : 0)
</script>

<template>
  <div class="metric-trend-chart">
    <svg v-if="points.length" :viewBox="`0 0 ${width} ${height}`" role="img" aria-label="30 日趋势">
      <line :x1="padding" :y1="height-padding" :x2="width-padding" :y2="height-padding" class="trend-axis" />
      <polyline :points="polyline" class="trend-line" fill="none" />
    </svg>
    <div v-else class="empty-state compact">暂无趋势数据</div>
    <div v-if="points.length" class="trend-chart-foot">
      <span>{{ points[0]?.date }}</span>
      <strong>峰值 {{ Number(maxValue).toLocaleString('zh-CN', { maximumFractionDigits: 2 }) }}</strong>
      <span>{{ points[points.length - 1]?.date }}</span>
    </div>
  </div>
</template>
