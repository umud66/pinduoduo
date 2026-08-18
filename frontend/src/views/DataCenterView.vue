<script setup>
import { useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app.js'
import SyncCenter from '@/components/data/SyncCenter.vue'
import CapabilityProbe from '@/components/data/CapabilityProbe.vue'
import BrowserDataBridge from '@/components/data/BrowserDataBridge.vue'
import ReportImport from '@/components/data/ReportImport.vue'
import { seedDemo } from '@/api/workspace.js'

const app = useAppStore()
const router = useRouter()
async function demo() {
  await seedDemo(app.selectedShopId)
  window.dispatchEvent(new CustomEvent('pdd:toast', { detail: { message: '演示数据已创建', type: 'success' } }))
  window.dispatchEvent(new CustomEvent('pdd:data-updated'))
}
</script>

<template>
  <section class="page-content">
    <article v-if="!app.selectedShopId" class="card empty-state">
      <strong>请先创建店铺</strong>
      <button class="button primary" @click="router.push('/settings')">去设置</button>
    </article>
    <div v-else class="two-column-layout">
      <div class="stack">
        <SyncCenter />
        <CapabilityProbe />
        <BrowserDataBridge />
        <ReportImport />
      </div>
      <aside class="stack">
        <article class="card">
          <p class="section-kicker">DATA PRIORITY</p>
          <h3>推荐顺序</h3>
          <ol class="helper-text">
            <li>能取得开放平台授权时优先使用 OpenAPI</li>
            <li>没有资质时可试验 Browser Data Bridge</li>
            <li>浏览器响应只进入发现层，不直接污染正式经营表</li>
            <li>稳定适配后再映射到 SKU/订单/售后标准模型</li>
            <li>官方导出报表仍是重要兜底数据源</li>
          </ol>
        </article>
        <article class="card">
          <p class="section-kicker">EXPERIMENT</p>
          <h3>为什么单独实验？</h3>
          <p class="helper-text">商家后台私有响应没有开放 API 稳定性保证。这个分支先验证真实页面、响应结构、登录保持和维护成本，再决定是否进入正式版本。</p>
        </article>
        <article class="card">
          <p class="section-kicker">DEMO</p><h3>没有真实数据？</h3>
          <p class="helper-text">生成演示数据体验完整诊断流程。</p>
          <button class="button ghost full" @click="demo">创建演示数据</button>
        </article>
      </aside>
    </div>
  </section>
</template>
