<script setup>
import { onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import {
  completePddAuthorization,
  disconnectPddAuthorization,
  getPddAuthorization,
  refreshPddAuthorization,
  savePddApplication,
  startPddAuthorization,
  probeAuthorizedShop,
} from '@/api/pdd-auth.js'

const props = defineProps({ shop: { type: Object, default: null } })
const emit = defineEmits(['updated'])
const loading = ref(false)
const state = ref(null)
const authUrl = ref('')
const manualCode = ref('')
const pendingState = ref('')
const probe = ref(null)
const form = reactive({
  client_id: '',
  client_secret: '',
  redirect_uri: '',
  auth_web_url: 'https://fuwu.pinduoduo.com/service-market/auth',
})
let timer = null

function toast(message, type = '') {
  window.dispatchEvent(new CustomEvent('pdd:toast', { detail: { message, type } }))
}
async function load() {
  if (!props.shop?.id) { state.value = null; return }
  try {
    state.value = await getPddAuthorization(props.shop.id)
    const app = state.value?.application
    if (app) {
      form.client_id = app.client_id || ''
      form.redirect_uri = app.redirect_uri || form.redirect_uri
      form.auth_web_url = app.auth_web_url || form.auth_web_url
      form.client_secret = ''
    }
    if (state.value?.authorization?.status === 'authorized') stopPolling()
  } catch (error) {
    toast(error.message, 'error')
  }
}
async function saveApplication() {
  loading.value = true
  try {
    await savePddApplication({
      client_id: form.client_id,
      client_secret: form.client_secret || null,
      redirect_uri: form.redirect_uri,
      auth_web_url: form.auth_web_url || null,
    })
    form.client_secret = ''
    await load()
    toast('拼多多开放平台应用设置已保存', 'success')
  } catch (error) { toast(error.message, 'error') }
  finally { loading.value = false }
}
async function startAuthorization() {
  if (!props.shop?.id) return toast('请先创建并选择店铺', 'error')
  loading.value = true
  try {
    const result = await startPddAuthorization(props.shop.id)
    authUrl.value = result.authorization_url
    pendingState.value = result.state
    const opened = window.open(result.authorization_url, '_blank')
    if (!opened) toast('浏览器拦截了授权窗口，请点击下方“打开拼多多授权页”', 'error')
    startPolling()
  } catch (error) { toast(error.message, 'error') }
  finally { loading.value = false }
}
async function submitCode() {
  if (!pendingState.value || !manualCode.value.trim()) return
  loading.value = true
  try {
    await completePddAuthorization(pendingState.value, manualCode.value.trim())
    manualCode.value = ''
    await load()
    emit('updated')
    toast('店铺授权已完成', 'success')
  } catch (error) { toast(error.message, 'error') }
  finally { loading.value = false }
}
async function refreshToken() {
  loading.value = true
  try { await refreshPddAuthorization(props.shop.id); await load(); emit('updated'); toast('授权凭证已刷新', 'success') }
  catch (error) { toast(error.message, 'error') }
  finally { loading.value = false }
}
async function disconnect() {
  if (!confirm('仅清除本机保存的授权凭证。确认断开？')) return
  await disconnectPddAuthorization(props.shop.id)
  authUrl.value = ''; pendingState.value = ''; probe.value = null
  await load(); emit('updated'); toast('已清除本机授权凭证', 'success')
}
async function runProbe() {
  loading.value = true
  try { probe.value = await probeAuthorizedShop(props.shop.id); toast('权限探测完成', 'success') }
  catch (error) { toast(error.message, 'error') }
  finally { loading.value = false }
}
function startPolling() {
  stopPolling()
  timer = window.setInterval(load, 3000)
}
function stopPolling() {
  if (timer) window.clearInterval(timer)
  timer = null
}
function receiveMessage(event) {
  if (event.origin === window.location.origin && event.data?.type === 'pdd-oauth-complete') load()
}
watch(() => props.shop?.id, load)
onMounted(() => { load(); window.addEventListener('message', receiveMessage) })
onBeforeUnmount(() => { stopPolling(); window.removeEventListener('message', receiveMessage) })
</script>

<template>
  <article class="card pdd-auth-card">
    <div class="card-heading">
      <div><p class="section-kicker">PDD AUTHORIZATION</p><h2>拼多多店铺授权</h2></div>
      <span class="status-pill" :class="state?.authorization?.status === 'authorized' ? 'success' : 'neutral'">
        {{ state?.authorization?.status === 'authorized' ? '已授权' : '未授权' }}
      </span>
    </div>

    <div class="form-note form-gap">
      Client ID / Secret 属于开放平台应用；Access Token 必须由店铺授权产生，普通流程不再手工填写 Token。
    </div>

    <form class="form-grid form-gap" @submit.prevent="saveApplication">
      <label class="field full">Client ID<input v-model="form.client_id" required></label>
      <label class="field full">Client Secret<input v-model="form.client_secret" type="password" :placeholder="state?.application?.has_client_secret ? '已保存，留空保持不变' : '首次配置必须填写'"></label>
      <label class="field full">授权回调地址<input v-model="form.redirect_uri" required placeholder="必须与开放平台应用详情一致；本地开发可验证 127.0.0.1 callback"></label>
      <details class="field full">
        <summary>高级：授权页地址</summary>
        <input v-model="form.auth_web_url">
      </details>
      <div class="form-note full">
        回调地址必须与拼多多开放平台应用详情中的配置完全一致。当前 endpoint 状态：{{ state?.application?.endpoint_status || 'unknown' }}；localhost 回调尚未经过真实店铺验证。
      </div>
      <div class="card-actions full"><button class="button secondary" :disabled="loading">保存开放平台应用</button></div>
    </form>

    <template v-if="shop">
      <div v-if="state?.authorization" class="auth-status-panel form-gap">
        <div><small>授权状态</small><strong>{{ state.authorization.status }}</strong></div>
        <div><small>授权账号</small><strong>{{ state.authorization.owner_name || '未返回名称' }}</strong></div>
        <div><small>Owner ID</small><strong>{{ state.authorization.owner_id || '—' }}</strong></div>
        <div><small>Access Token 到期</small><strong>{{ state.authorization.access_expires_at || '平台未返回' }}</strong></div>
        <div><small>Refresh Token 到期</small><strong>{{ state.authorization.refresh_expires_at || '平台未返回' }}</strong></div>
        <div class="full"><small>Scope</small><strong>{{ state.authorization.scopes?.length ? state.authorization.scopes.join('、') : '平台未返回 scope' }}</strong></div>
        <div v-if="state.authorization.last_error" class="form-note full">{{ state.authorization.last_error }}</div>
        <div class="card-actions full">
          <button class="button ghost" :disabled="loading" @click="runProbe">权限探测</button>
          <button v-if="state.authorization.can_refresh" class="button secondary" :disabled="loading" @click="refreshToken">刷新授权</button>
          <button v-if="state.authorization.status !== 'authorized'" class="button primary" :disabled="loading" @click="startAuthorization">重新授权</button>
          <button class="button danger" :disabled="loading" @click="disconnect">断开本机授权</button>
        </div>
      </div>
      <div v-else class="auth-start-panel form-gap">
        <p>当前店铺：<strong>{{ shop.name }}</strong></p>
        <button class="button primary" :disabled="loading || !state?.application?.client_id" @click="startAuthorization">绑定拼多多店铺</button>
        <a v-if="authUrl" class="button ghost" :href="authUrl" target="_blank" rel="noopener">打开拼多多授权页</a>
      </div>
    </template>

    <details v-if="pendingState" class="manual-code-box">
      <summary>开发模式：手工提交回调 code</summary>
      <p class="helper-text">仅用于回调地址暂时不能直达本机时调试；正式商家流程应由回调自动完成。</p>
      <input v-model="manualCode" placeholder="粘贴授权回调中的 code">
      <button class="button ghost" :disabled="loading || !manualCode.trim()" @click="submitCode">提交 code</button>
    </details>

    <div v-if="probe" class="probe-list form-gap">
      <div v-for="item in probe.items" :key="item.api_type" class="probe-row">
        <span><strong>{{ item.api_type }}</strong><small>{{ item.message }}</small></span>
        <span class="status-pill" :class="item.status">{{ item.status }}</span>
      </div>
    </div>
  </article>
</template>
