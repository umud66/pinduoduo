<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { type: Number, default: null },
  inverse: { type: Boolean, default: false },
  empty: { type: String, default: '—' },
})

const state = computed(() => {
  if (props.value === null || props.value === undefined || Number.isNaN(Number(props.value))) return 'unknown'
  const n = Number(props.value)
  if (Math.abs(n) < 0.03) return 'flat'
  const positive = n > 0
  if (props.inverse) return positive ? 'bad' : 'good'
  return positive ? 'good' : 'bad'
})

const label = computed(() => {
  if (state.value === 'unknown') return props.empty
  const n = Number(props.value)
  const arrow = n > 0 ? '↑' : n < 0 ? '↓' : '→'
  return `${arrow} ${Math.abs(n * 100).toFixed(1)}%`
})
</script>

<template>
  <span class="trend-delta" :class="state">{{ label }}</span>
</template>
