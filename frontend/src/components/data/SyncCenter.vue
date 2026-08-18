<script setup>
import { computed, onMounted } from 'vue'
import { useAppStore } from '@/stores/app.js'
import { useSyncStore } from '@/stores/sync.js'
import { retrySync, saveSyncPreference, startSync } from '@/api/sync.js'
import StatusTag from '@/components/StatusTag.vue'
const app=useAppStore(); const sync=useSyncStore(); const status=computed(()=>sync.status)
async function run(type){await startSync(app.selectedShopId,type);toast('同步任务已提交','success');sync.startPolling(app.selectedShopId)}
async function retry(id){await retrySync(id);toast('重试任务已提交','success');sync.startPolling(app.selectedShopId)}
async function preference(event){const auto=event.target.checked;await saveSyncPreference(app.selectedShopId,{auto_sync:auto,interval_minutes:Number(status.value?.preference?.interval_minutes||30)});await sync.refresh(app.selectedShopId)}
function toast(message,type=''){window.dispatchEvent(new CustomEvent('pdd:toast',{detail:{message,type}}))}
onMounted(()=>sync.startPolling(app.selectedShopId))
</script>
<template><article class="card"><div class="card-heading"><div><p class="section-kicker">PDD SYNC</p><h2>拼多多自动同步</h2></div><StatusTag :value="status?.active?'running':status?.configured?'success':'neutral'" :label="status?.active?'同步中':status?.configured?'已就绪':'未配置'"/></div><div class="sync-summary"><div><small>商品</small><strong>{{status?.product_count||0}}</strong></div><div><small>SKU</small><strong>{{status?.sku_count||0}}</strong></div><div><small>订单游标</small><strong>{{status?.cursors?.orders?.last_synced_at_iso||'从未'}}</strong></div><div><small>售后游标</small><strong>{{status?.cursors?.refunds?.last_synced_at_iso||'从未'}}</strong></div></div><div class="sync-actions"><button class="button primary" :disabled="status?.active||!status?.configured" @click="run('full')">首次/全量同步</button><button class="button secondary" :disabled="status?.active||!status?.configured" @click="run('incremental')">立即增量同步</button><button class="button ghost" :disabled="status?.active||!status?.configured" @click="run('products')">只同步商品</button></div><label class="switch"><input type="checkbox" :checked="status?.preference?.auto_sync" :disabled="!status?.configured" @change="preference"> 自动同步</label><div class="sync-job-list"><div v-for="job in status?.jobs||[]" :key="job.id" class="sync-job-row"><span><strong>{{job.job_type}}</strong><small>{{job.stats?.stage||job.status}} · {{job.created_at}}</small><small v-if="job.error_message" class="danger-text">{{job.error_message}}</small></span><span><StatusTag :value="job.status"/><button v-if="job.retryable" class="button ghost" @click="retry(job.id)">重试</button></span></div></div></article></template>
