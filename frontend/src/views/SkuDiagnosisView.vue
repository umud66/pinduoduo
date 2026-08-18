<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { listSkus } from '@/api/workspace.js'
import { diagnoseShop } from '@/api/diagnosis.js'
import { useAppStore } from '@/stores/app.js'
import SkuDrawer from '@/components/SkuDrawer.vue'
import StatusTag from '@/components/StatusTag.vue'
const app=useAppStore(); const q=ref(''); const severity=ref('all'); const items=ref([]); const loading=ref(false); const drawer=ref(null); let timer
const money=(v)=>`¥${Number(v||0).toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2})}`
async function load(){if(!app.selectedShopId)return;loading.value=true;try{items.value=(await listSkus(app.selectedShopId,q.value,severity.value)).items||[]}finally{loading.value=false}}
async function runAll(){const r=await diagnoseShop(app.selectedShopId);toast(`诊断完成：${r.success} 个 SKU`,'success');await load()}
function toast(message,type=''){window.dispatchEvent(new CustomEvent('pdd:toast',{detail:{message,type}}))}
watch([q,severity],()=>{clearTimeout(timer);timer=setTimeout(load,220)}); function updated(){load()}; onMounted(()=>{load();window.addEventListener('pdd:data-updated',updated)});onBeforeUnmount(()=>window.removeEventListener('pdd:data-updated',updated))
</script>
<template><section class="page-content"><div class="toolbar card compact"><input v-model="q" type="search" placeholder="搜索商品名、SKU、商品 ID"><select v-model="severity"><option value="all">全部状态</option><option value="high">严重</option><option value="medium">关注</option><option value="low">轻微</option><option value="healthy">健康</option><option value="unrun">未诊断</option></select><button class="button primary" :disabled="loading||!app.selectedShopId" @click="runAll">批量诊断</button></div><article class="card"><div class="card-heading"><div><p class="section-kicker">SKU WORKBENCH</p><h2>SKU 经营状态</h2></div><span>{{items.length}} 个 SKU</span></div><div class="table-wrap"><table class="data-table"><thead><tr><th>商品 / SKU</th><th>销量</th><th>GMV</th><th>库存</th><th>健康度</th><th>主要问题</th><th></th></tr></thead><tbody><tr v-for="item in items" :key="item.id"><td><div class="product-line"><img v-if="item.image_url" class="product-thumb" :src="item.image_url"><span v-else class="product-thumb"></span><span><strong>{{item.product_title}}</strong><small>{{item.sku_name}} · {{item.platform_sku_id}}</small></span></div></td><td>{{item.metric?.sales_qty??0}}</td><td>{{money(item.metric?.gmv)}}</td><td>{{item.stock??item.metric?.stock??'—'}}</td><td><StatusTag :value="item.diagnosis?.severity||'neutral'"/> {{item.diagnosis?.health_score??'—'}}</td><td>{{item.diagnosis?.main_issue||'尚未诊断'}}</td><td><button class="button ghost" @click="drawer?.show(item.id)">查看</button></td></tr></tbody></table></div><div v-if="!loading&&!items.length" class="empty-state">没有匹配的 SKU</div></article><SkuDrawer ref="drawer"/></section></template>
