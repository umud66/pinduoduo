<script setup>
const props = defineProps({ priority: { type: Object, default: null } })
const bandLabel = (value) => ({ urgent: '立即处理', high: '高优先', medium: '关注', normal: '常规', unavailable: '待诊断' }[value] || '未知')
</script>

<template>
  <article class="card decision-card decision-priority-card">
    <div class="card-heading">
      <div><p class="section-kicker">ACTION PRIORITY</p><h3>运营处理优先级</h3></div>
      <span class="status-pill" :class="priority?.band === 'urgent' ? 'high' : priority?.band === 'high' ? 'medium' : 'neutral'">{{ bandLabel(priority?.band) }}</span>
    </div>
    <div v-if="priority?.available" class="priority-score-grid">
      <div><small>规则优先级</small><strong>{{ priority.base_priority }}</strong></div>
      <div class="priority-plus">+</div>
      <div><small>趋势上下文</small><strong>+{{ priority.boost }}</strong></div>
      <div class="priority-equals">=</div>
      <div class="priority-final"><small>当前行动优先级</small><strong>{{ priority.action_priority }}</strong></div>
    </div>
    <div v-if="priority?.adjustments?.length" class="priority-adjustments">
      <div v-for="item in priority.adjustments" :key="item.code" class="priority-adjustment-row">
        <span><strong>{{ item.code }}</strong><small>{{ item.reason }}</small></span>
        <strong>+{{ item.points }}</strong>
      </div>
    </div>
    <p v-else-if="priority?.available" class="helper-text">当前没有趋势上下文需要额外提高处理顺序，保持规则诊断优先级。</p>
    <p v-else class="helper-text">需要先运行确定性诊断，系统才会在其 priority_score 基础上计算行动优先级。</p>
    <p v-if="priority?.note" class="decision-note">{{ priority.note }}</p>
  </article>
</template>
