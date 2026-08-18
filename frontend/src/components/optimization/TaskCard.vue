<script setup>
import { ref } from 'vue'
import ReviewTimeline from './ReviewTimeline.vue'

const props = defineProps({ task: { type: Object, required: true } })
const emit = defineEmits(['start', 'complete', 'cancel', 'refresh'])
const note = ref(props.task.action?.execution_note || '')
const statusText = (value) => ({ planned: '待执行', in_progress: '执行中', completed: '已完成', cancelled: '已取消' }[value] || value)
const outcomeText = (value) => ({ improved: '最近复盘：改善', worsened: '最近复盘：恶化', stable_or_mixed: '最近复盘：持平/混合' }[value] || '')
</script>

<template>
  <article class="optimization-task card">
    <header class="optimization-task-head">
      <div>
        <p class="section-kicker">{{ task.issue_code || 'MANUAL ACTION' }}</p>
        <h3>{{ task.title }}</h3>
        <p class="helper-text">{{ task.product?.title }} · {{ task.sku?.name }}</p>
      </div>
      <div class="task-state"><span class="status-pill" :class="task.status">{{ statusText(task.status) }}</span><strong v-if="task.latest_outcome">{{ outcomeText(task.latest_outcome) }}</strong></div>
    </header>

    <div class="task-action-box">
      <small>执行动作</small>
      <strong>{{ task.action?.action }}</strong>
      <p v-if="task.action?.reason">{{ task.action.reason }}</p>
      <div class="field-tags"><span v-for="metric in task.action?.validation_metrics || []" :key="metric" class="field-tag">观察 {{ metric }}</span></div>
    </div>

    <div v-if="task.started_at" class="task-time-row"><span>开始 {{ task.started_at }}</span><span v-if="task.completed_at">完成 {{ task.completed_at }}</span></div>
    <ReviewTimeline :reviews="task.reviews || []" />

    <label v-if="task.status === 'in_progress'" class="field">执行记录
      <textarea v-model="note" placeholder="例如：8月18日更换主图，仅调整首屏卖点，其余变量保持不变"></textarea>
    </label>

    <div class="card-actions task-actions">
      <button v-if="task.started_at && task.status !== 'cancelled'" class="button ghost" @click="emit('refresh', task.id)">刷新复盘</button>
      <button v-if="task.status === 'planned'" class="button secondary" @click="emit('start', task.id)">开始执行</button>
      <button v-if="task.status === 'in_progress'" class="button primary" @click="emit('complete', task.id, note)">标记完成</button>
      <button v-if="['planned','in_progress'].includes(task.status)" class="button danger" @click="emit('cancel', task.id)">取消任务</button>
    </div>
  </article>
</template>
