<script setup>
import { ref } from 'vue'
import { useAppStore } from '@/stores/app.js'
import { probeCapabilities } from '@/api/sync.js'
import StatusTag from '@/components/StatusTag.vue'
const app=useAppStore(); const result=ref(null); const loading=ref(false)
async function run(){loading.value=true;try{result.value=await probeCapabilities(app.selectedShopId)}finally{loading.value=false}}
</script>
<template><article class="card"><div class="card-heading"><div><p class="section-kicker">CAPABILITY PROBE</p><h2>API 能力检测</h2></div></div><p class="helper-text">低频只读检测，确认当前授权实际可用能力。</p><button class="button secondary" :disabled="loading" @click="run">{{loading?'检测中…':'运行能力检测'}}</button><div class="probe-list"><div v-for="item in result?.items||[]" :key="item.api_type" class="probe-row"><span><strong>{{item.api_type}}</strong><small>{{item.message}}</small></span><StatusTag :value="item.status==='ok'?'success':item.status==='denied'?'medium':'failed'" :label="item.status"/></div></div></article></template>
