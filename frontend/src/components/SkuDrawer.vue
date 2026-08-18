<script setup>
import { computed, ref } from 'vue'
import { getSku, getSkuInsights } from '@/api/workspace.js'
import { analyzeDiagnosis, diagnoseSku } from '@/api/diagnosis.js'
import { useAppStore } from '@/stores/app.js'
import DiagnosisPanel from '@/components/diagnosis/DiagnosisPanel.vue'
import PeerComparison from '@/components/insights/PeerComparison.vue'
import SkuTrendPanel from '@/components/insights/SkuTrendPanel.vue'

const app = useAppStore()
const open = ref(false)
const loading = ref(false)
const data = ref(null)
const insights = ref(null)
const error = ref('')
const money = (value) => `¥${Number(value || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
const percent = (value) => value === null || value === undefined ? '—' : `${(Number(value) * 100).toFixed(1)}%`
const diagnosisId = computed(() => data.value?.diagnosis?.id || data.value?.diagnosis?.diagnosis_id)

async function show(id) {
  open.value = true
  loading.value = true
  error.value = ''
  insights.value = null
  try {
    const [detail, trend] = await Promise.all([getSku(id), getSkuInsights(id)])
    data.value = detail
    insights.value = trend
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function rerun() {
  if (!data.value?.id) return
  await diagnoseSku(data.value.id)
  await show(data.value.id)
  toast('诊断与持续性分析已刷新', 'success')
  window.dispatchEvent(new CustomEvent('pdd:data-updated'))
}

async function ai() {
  const provider = app.activeProvider
  if (!provider || !diagnosisId.value) return toast('请先配置可用 AI Provider', 'error')
  await analyzeDiagnosis(diagnosisId.value, provider.id)
  await show(data.value.id)
  toast('AI 建议已生成', 'success')
}

function toast(message, type = '') {
  window.dispatchEvent(new CustomEvent('pdd:toast', { detail: { message, type } }))
}

defineExpose({ show })
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="drawer-backdrop" @click="open = false"></div>
    <aside class="drawer drawer-wide" :class="{ open }" :aria-hidden="!open">
      <header class="drawer-head">
        <div><p class="section-kicker">SKU DETAIL</p><h2>{{ data?.sku_name || 'SKU 详情' }}</h2></div>
        <button class="icon-button" @click="open = false">×</button>
      </header>
      <div class="drawer-content">
        <div v-if="loading" class="loading-block">正在读取 SKU 诊断与趋势…</div>
        <div v-else-if="error" class="empty-state">{{ error }}</div>
        <div v-else-if="data" class="stack">
          <article class="card compact sku-identity-card">
            <div>
              <p class="section-kicker">PRODUCT</p>
              <h3>{{ data.product?.title }}</h3>
              <p class="helper-text">{{ data.sku_name }} · SKU {{ data.platform_sku_id }}</p>
            </div>
            <div class="sku-identity-meta"><span>价格 {{ money(data.price) }}</span><span>库存 {{ data.stock ?? '—' }}</span></div>
          </article>

          <div class="metric-grid metric-grid-six">
            <div class="metric-box"><small>销量</small><strong>{{ data.latest_metric?.sales_qty ?? 0 }}</strong></div>
            <div class="metric-box"><small>GMV</small><strong>{{ money(data.latest_metric?.gmv) }}</strong></div>
            <div class="metric-box"><small>CTR</small><strong>{{ percent(data.latest_metric?.ctr) }}</strong></div>
            <div class="metric-box"><small>CVR</small><strong>{{ percent(data.latest_metric?.cvr) }}</strong></div>
            <div class="metric-box"><small>退款率</small><strong>{{ percent(data.latest_metric?.refund_rate) }}</strong></div>
            <div class="metric-box"><small>推广 ROI</small><strong>{{ data.latest_metric?.ad_roi === null || data.latest_metric?.ad_roi === undefined ? '—' : Number(data.latest_metric.ad_roi).toFixed(2) }}</strong></div>
          </div>

          <SkuTrendPanel :insights="insights" />
          <PeerComparison v-if="insights" :comparison="insights.peer_comparison" />
          <DiagnosisPanel :diagnosis="data.diagnosis" />

          <div class="sticky-actions">
            <button class="button secondary" @click="rerun">重新诊断</button>
            <button v-if="app.providers.length" class="button primary" @click="ai">生成 AI 建议</button>
          </div>
        </div>
      </div>
    </aside>
  </Teleport>
</template>
