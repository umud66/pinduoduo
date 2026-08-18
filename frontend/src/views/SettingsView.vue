<script setup>
import { computed, reactive } from 'vue'
import { useAppStore } from '@/stores/app.js'
import { createShop, updateShop } from '@/api/shop.js'
import { createProvider, deleteProvider, testProvider } from '@/api/ai.js'
import PddAuthorizationSettings from '@/components/settings/PddAuthorizationSettings.vue'

const app = useAppStore()
const shop = computed(() => app.currentShop)
const shopForm = reactive({ name: '' })
const provider = reactive({
  name: '', provider_type: 'openai_compatible', base_url: 'https://api.openai.com/v1',
  api_key: '', chat_model: '', vision_model: '', image_model: '',
})

function hydrate() { shopForm.name = shop.value?.name || '' }
app.$subscribe(() => hydrate())
hydrate()

function toast(message, type = '') {
  window.dispatchEvent(new CustomEvent('pdd:toast', { detail: { message, type } }))
}
async function saveShop() {
  const payload = { name: shopForm.name }
  if (shop.value) await updateShop(shop.value.id, payload)
  else await createShop(payload)
  await app.refresh()
  hydrate()
  toast('店铺基本信息已保存', 'success')
}
async function authorizationUpdated() {
  await app.refresh()
  window.dispatchEvent(new CustomEvent('pdd:data-updated'))
}
async function saveProvider() {
  await createProvider({
    ...provider,
    chat_model: provider.chat_model || null,
    vision_model: provider.vision_model || null,
    image_model: provider.image_model || null,
  })
  await app.refresh()
  provider.api_key = ''
  toast('Provider 已保存', 'success')
}
async function test(id) { await testProvider(id); toast('模型连接正常', 'success') }
async function remove(id) {
  if (!confirm('确定删除这个 Provider？')) return
  await deleteProvider(id)
  await app.refresh()
  toast('Provider 已删除', 'success')
}
</script>

<template>
  <section class="page-content">
    <div class="settings-grid">
      <div class="stack">
        <article class="card">
          <div class="card-heading">
            <div><p class="section-kicker">SHOP</p><h2>{{ shop ? '店铺基本信息' : '创建店铺' }}</h2></div>
          </div>
          <form class="form-grid form-gap" @submit.prevent="saveShop">
            <label class="field full">店铺名称<input v-model="shopForm.name" required></label>
            <div class="form-note full">店铺名称只是本地识别名称；拼多多真实店铺身份由下面的授权结果绑定。</div>
            <div class="card-actions full"><button class="button primary" type="submit">保存店铺</button></div>
          </form>
        </article>
        <PddAuthorizationSettings :shop="shop" @updated="authorizationUpdated" />
      </div>

      <article class="card">
        <div class="card-heading"><div><p class="section-kicker">AI PROVIDERS</p><h2>模型与中转站</h2></div></div>
        <div class="provider-list">
          <div v-for="item in app.providers" :key="item.id" class="provider-row">
            <span><strong>{{ item.name }}</strong><small>{{ item.provider_type }} · {{ item.chat_model || '未设聊天模型' }}</small></span>
            <span><button class="button ghost" @click="test(item.id)">测试</button> <button class="button danger" @click="remove(item.id)">删除</button></span>
          </div>
          <div v-if="!app.providers.length" class="empty-state">还没有配置 AI Provider</div>
        </div>
        <details open>
          <summary>添加模型服务</summary>
          <form class="form-grid form-gap" @submit.prevent="saveProvider">
            <label class="field">名称<input v-model="provider.name" required></label>
            <label class="field">类型<select v-model="provider.provider_type"><option value="openai_compatible">OpenAI Compatible</option><option value="anthropic">Anthropic</option><option value="gemini">Gemini</option></select></label>
            <label class="field full">Base URL<input v-model="provider.base_url" required></label>
            <label class="field full">API Key<input v-model="provider.api_key" type="password" required></label>
            <label class="field">聊天模型<input v-model="provider.chat_model"></label>
            <label class="field">图片模型<input v-model="provider.image_model"></label>
            <label class="field full">视觉模型<input v-model="provider.vision_model"></label>
            <div class="card-actions full"><button class="button secondary" type="submit">保存 Provider</button></div>
          </form>
        </details>
      </article>
    </div>
  </section>
</template>
