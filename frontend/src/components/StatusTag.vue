<script setup>
defineProps({ value: { type: String, default: 'neutral' }, label: { type: String, default: '' } })
const labels = { high: '严重', medium: '关注', low: '轻微', healthy: '健康', success: '成功', failed: '失败', running: '同步中', queued: '排队中', neutral: '未知' }
</script>
<template><span class="status-pill" :class="value">{{ label || labels[value] || value }}</span></template>
