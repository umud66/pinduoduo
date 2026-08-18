<script setup>
import { computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app.js'
import { useSyncStore } from '@/stores/sync.js'
import StatusTag from '@/components/StatusTag.vue'
import ToastHost from '@/components/ToastHost.vue'

const route = useRoute()
const app = useAppStore()
const sync = useSyncStore()
const nav = [
  ['/dashboard', '经营总览'], ['/skus', 'SKU 诊断'], ['/tasks', '优化任务'], ['/data', '数据中心'], ['/ai', 'AI 工作台'], ['/settings', '设置'],
]
const syncLabel = computed(() => {
  if (!app.selectedShopId) return ['neutral', '未选择店铺']
  if (!sync.status?.configured) return ['neutral', 'PDD 未配置']
  if (sync.status?.active) return ['running', '数据同步中']
  if (sync.status?.latest_failed_job_id && !sync.status?.latest_success_job_id) return ['failed', '最近同步失败']
  return ['success', '同步已就绪']
})
async function bootstrap() { await app.refresh(); if (app.selectedShopId) sync.startPolling(app.selectedShopId) }
function changeShop(event) { app.selectShop(event.target.value); sync.startPolling(app.selectedShopId); window.dispatchEvent(new CustomEvent('pdd:shop-changed')) }
watch(() => app.selectedShopId, (id) => { if (id) sync.startPolling(id) })
onMounted(bootstrap)
</script>
<template>
  <div class="app-shell">
    <aside class="sidebar">
      <RouterLink class="brand" to="/dashboard"><span class="brand-mark">P</span><span><strong>拼多多 AI 运营助手</strong><small>本地运营工作台</small></span></RouterLink>
      <nav class="nav-list"><RouterLink v-for="item in nav" :key="item[0]" :to="item[0]" class="nav-item">{{ item[1] }}</RouterLink></nav>
      <div class="sidebar-foot"><span class="local-badge">● 数据保存在本机</span><span>Vue 3 工作台</span></div>
    </aside>
    <main class="main-area">
      <header class="topbar">
        <div><p class="page-kicker">{{ route.meta.kicker }}</p><h1>{{ route.meta.title }}</h1></div>
        <div class="topbar-actions"><StatusTag :value="syncLabel[0]" :label="syncLabel[1]"/><label class="shop-switcher">当前店铺<select :value="app.selectedShopId || ''" @change="changeShop"><option v-if="!app.shops.length" value="">暂无店铺</option><option v-for="shop in app.shops" :key="shop.id" :value="shop.id">{{ shop.name }}</option></select></label></div>
      </header>
      <RouterView :key="`${route.fullPath}-${app.selectedShopId || 0}`" />
    </main>
    <ToastHost />
  </div>
</template>
