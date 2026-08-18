<script setup>
import { ref } from 'vue'
import { useAppStore } from '@/stores/app.js'
import { jsonRequest, request } from '@/api/http.js'
const app=useAppStore(); const preview=ref(null); const loading=ref(false)
async function choose(event){const file=event.target.files?.[0];if(!file)return;loading.value=true;const form=new FormData();form.append('file',file);try{preview.value=await request('/api/reports/preview',{method:'POST',body:form})}finally{loading.value=false}}
async function confirm(){const r=await jsonRequest('/api/reports/import','POST',{shop_id:app.selectedShopId,stored_as:preview.value.stored_as});toast(`导入完成：${r.summary?.rows_imported||0} 行`,'success');window.dispatchEvent(new CustomEvent('pdd:data-updated'))}
function toast(message,type=''){window.dispatchEvent(new CustomEvent('pdd:toast',{detail:{message,type}}))}
</script>
<template><article class="card"><div class="card-heading"><div><p class="section-kicker">REPORT IMPORT</p><h2>经营报表导入</h2></div></div><label class="drop-zone"><input type="file" accept=".csv,.xlsx,.xlsm" hidden @change="choose"><strong>{{loading?'正在识别…':'选择 CSV / XLSX 报表'}}</strong><span>补充曝光、点击、推广等 API 未必可获得的指标</span></label><div v-if="preview" class="report-preview"><div class="field-tags"><span v-for="(header,field) in preview.detected_fields" :key="field" class="field-tag">{{field}} ← {{header}}</span></div><p v-if="!preview.can_import" class="danger-text">缺少：{{preview.missing_required?.join(', ')}}</p><button class="button primary" :disabled="!preview.can_import" @click="confirm">确认导入</button></div></article></template>
