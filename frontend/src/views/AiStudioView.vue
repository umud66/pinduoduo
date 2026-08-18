<script setup>
import { ref } from 'vue'
import { useAppStore } from '@/stores/app.js'
import { aiChat, generateImage } from '@/api/ai.js'
const app=useAppStore(); const prompt=ref('');const output=ref('');const imagePrompt=ref('');const images=ref([]);const loading=ref(false)
async function chat(){const p=app.activeProvider;if(!p)return toast('请先配置 AI Provider','error');loading.value=true;try{const r=await aiChat(p.id, prompt.value);output.value=r.text||JSON.stringify(r,null,2)}finally{loading.value=false}}
async function image(){const p=app.activeProvider;if(!p)return toast('请先配置 AI Provider','error');loading.value=true;try{const r=await generateImage(p.id, imagePrompt.value);images.value=(r.urls||[]).map(url=>({url})); if(r.base64_images?.length) images.value.push(...r.base64_images.map(value=>({url:`data:image/png;base64,${value}`})))}finally{loading.value=false}}
function toast(message,type=''){window.dispatchEvent(new CustomEvent('pdd:toast',{detail:{message,type}}))}
</script>
<template><section class="page-content"><div class="two-column-layout"><article class="card"><p class="section-kicker">OPERATIONS CHAT</p><h2>运营对话</h2><textarea v-model="prompt" class="tall" placeholder="例如：结合当前诊断，给我一个今日优先处理清单"></textarea><div class="card-actions"><button class="button primary" :disabled="loading||!prompt" @click="chat">发送给 AI</button></div><div v-if="output" class="ai-result">{{output}}</div></article><article class="card"><p class="section-kicker">IMAGE</p><h2>商品素材生成</h2><textarea v-model="imagePrompt" placeholder="描述需要生成的商品主图或场景图"></textarea><div class="card-actions"><button class="button secondary" :disabled="loading||!imagePrompt" @click="image">生成图片</button></div><div class="image-grid"><img v-for="(item,index) in images" :key="index" :src="item.url||item"></div></article></div></section></template>
