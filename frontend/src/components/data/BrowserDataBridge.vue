<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useAppStore } from '@/stores/app.js'
import {
  getBrowserBridgeSession,
  getBrowserBridgeStatus,
  listBrowserBridgeRecords,
  listBrowserBridgeSessions,
  startBrowserBridge,
  stopBrowserBridge,
} from '@/api/browser-bridge.js'

const app = useAppStore()
const status = ref(null)
const sessions = ref([])
const records = ref([])
const currentSession = ref(null)
const loading = ref(false)
const category = ref('all')
const startUrl = ref(localStorage.getItem('pdd-browser-start-url') || '')
const allowedDomains = ref('pinduoduo.com, yangkeduo.com')
let timer = null

const categoryCounts = computed(() => {
  const counts = { goods: 0, orders: 0, refunds: 0, traffic: 0, promotion: 0, unknown: 0 }
  for (const item of records.value) counts[item.category] = (counts[item.category] || 0) + 1
  return counts
})

function toast(message, type = '') {
  window.dispatchEvent(new CustomEvent('pdd:toast', { detail: { message, type } }))
}
function domains() {
  return allowedDomains.value.split(',').map((item) => item.trim()).filter(Boolean)
}
async function load({ quiet = true } = {}) {
  if (!app.selectedShopId) return
  try {
    status.value = await getBrowserBridgeStatus()
    sessions.value = (await listBrowserBridgeSessions(app.selectedShopId, 12)).items || []
    const sessionId = status.value?.active_session_id || currentSession.value?.id || sessions.value[0]?.id
    if (sessionId) {
      currentSession.value = await getBrowserBridgeSession(sessionId)
      records.value = (await listBrowserBridgeRecords(sessionId, category.value, 80)).items || []
    } else {
      currentSession.value = null
      records.value = []
    }
  } catch (error) {
    if (!quiet) toast(error.message, 'error')
  }
}
async function start() {
  if (!startUrl.value.trim()) return toast('请填写拼多多商家后台起始地址', 'error')
  loading.value = true
  try {
    localStorage.setItem('pdd-browser-start-url', startUrl.value.trim())
    const result = await startBrowserBridge({
      shop_id: app.selectedShopId,
      start_url: startUrl.value.trim(),
      allowed_domains: domains(),
    })
    currentSession.value = { id: result.session_id, status: 'starting' }
    toast('浏览器已启动，请在新窗口中自行登录并进入需要分析的页面', 'success')
    await load()
  } catch (error) { toast(error.message, 'error') }
  finally { loading.value = false }
}
async function stop() {
  loading.value = true
  try {
    await stopBrowserBridge()
    toast('正在结束浏览器采集会话', 'success')
    await load()
  } catch (error) { toast(error.message, 'error') }
  finally { loading.value = false }
}
function selectSession(item) {
  currentSession.value = item
  load({ quiet: true })
}
watch(() => app.selectedShopId, () => load({ quiet: true }))
watch(category, () => load({ quiet: true }))
onMounted(() => {
  load({ quiet: true })
  timer = window.setInterval(() => load({ quiet: true }), 2500)
})
onBeforeUnmount(() => { if (timer) window.clearInterval(timer) })
</script>

<template>
  <article class="card browser-bridge-card">
    <div class="card-heading">
      <div><p class="section-kicker">BROWSER DATA BRIDGE</p><h2>浏览器网络响应实验</h2></div>
      <span class="status-pill" :class="status?.running ? 'success' : 'neutral'">
        {{ status?.running ? '采集中' : '未运行' }}
      </span>
    </div>

    <div v-if="status && !status.available" class="browser-bridge-warning">
      <strong>浏览器采集组件未安装</strong>
      <p>{{ status.install_hint }}</p>
    </div>

    <div class="form-note">
      实验分支只观察用户已登录页面自己收到的 JSON 响应。不会读取或保存密码、验证码、Cookie、Authorization 请求头或请求体；当前不会自动把未知响应写入订单/SKU 正式表。
    </div>

    <div class="form-grid form-gap">
      <label class="field full">商家后台起始地址
        <input v-model="startUrl" placeholder="粘贴你实际使用的拼多多商家后台 https:// 地址">
      </label>
      <label class="field full">允许采集的域名
        <input v-model="allowedDomains" placeholder="pinduoduo.com, yangkeduo.com">
      </label>
      <div class="card-actions full">
        <button v-if="!status?.running" class="button primary" :disabled="loading || !status?.available" @click="start">打开浏览器并开始观察</button>
        <button v-else class="button danger" :disabled="loading" @click="stop">停止采集</button>
      </div>
    </div>

    <div v-if="currentSession" class="browser-session-summary">
      <div><small>会话</small><strong>#{{ currentSession.id }}</strong></div>
      <div><small>状态</small><strong>{{ currentSession.status }}</strong></div>
      <div><small>已记录</small><strong>{{ currentSession.captured_count || 0 }}</strong></div>
      <div><small>已跳过</small><strong>{{ currentSession.skipped_count || 0 }}</strong></div>
    </div>

    <div v-if="records.length" class="browser-category-strip">
      <button v-for="name in ['all','goods','orders','refunds','traffic','promotion','unknown']" :key="name" class="browser-category-button" :class="{ active: category === name }" @click="category = name">
        {{ name }}<span v-if="name !== 'all'">{{ categoryCounts[name] || 0 }}</span>
      </button>
    </div>

    <div class="browser-record-list">
      <div v-for="item in records" :key="item.id" class="browser-record-row">
        <div class="browser-record-main">
          <span class="status-pill neutral">{{ item.category }}</span>
          <strong>{{ item.method }} · {{ item.status_code }}</strong>
          <code>{{ item.url }}</code>
          <small v-if="item.query_keys?.length">query keys: {{ item.query_keys.join(', ') }}</small>
        </div>
        <div class="browser-record-meta">
          <span>{{ Math.round((item.body_bytes || 0) / 1024) }} KB</span>
          <span v-if="item.redacted_fields">脱敏 {{ item.redacted_fields }}</span>
          <span v-if="item.evidence?.length">{{ item.evidence.join(' / ') }}</span>
          <span v-if="item.capture_error">{{ item.capture_error }}</span>
        </div>
      </div>
      <div v-if="currentSession && !records.length" class="empty-state compact">
        还没有捕获到符合规则的 JSON 响应。请在打开的浏览器中登录并浏览经营、商品、订单、售后或推广页面。
      </div>
    </div>

    <details v-if="sessions.length" class="browser-session-history">
      <summary>最近采集会话</summary>
      <button v-for="item in sessions" :key="item.id" class="browser-session-history-row" @click="selectSession(item)">
        <span>#{{ item.id }} · {{ item.status }}</span><span>{{ item.captured_count }} responses</span>
      </button>
    </details>
  </article>
</template>
