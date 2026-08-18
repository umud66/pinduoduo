<script setup>
import { useRouter } from 'vue-router'
import { useAppStore } from '@/stores/app.js'
import SyncCenter from '@/components/data/SyncCenter.vue'
import CapabilityProbe from '@/components/data/CapabilityProbe.vue'
import ReportImport from '@/components/data/ReportImport.vue'
import { seedDemo } from '@/api/workspace.js'
const app=useAppStore();const router=useRouter()
async function demo(){await seedDemo(app.selectedShopId);window.dispatchEvent(new CustomEvent('pdd:toast',{detail:{message:'演示数据已创建',type:'success'}}));window.dispatchEvent(new CustomEvent('pdd:data-updated'))}
</script>
<template><section class="page-content"><article v-if="!app.selectedShopId" class="card empty-state"><strong>请先创建店铺</strong><button class="button primary" @click="router.push('/settings')">去设置</button></article><div v-else class="two-column-layout"><div class="stack"><SyncCenter/><CapabilityProbe/><ReportImport/></div><aside class="stack"><article class="card"><p class="section-kicker">DATA PRIORITY</p><h3>推荐顺序</h3><ol class="helper-text"><li>配置拼多多授权</li><li>运行能力检测</li><li>执行首次同步</li><li>导入曝光/点击/推广报表</li><li>查看自动诊断结果</li></ol></article><article class="card"><p class="section-kicker">DEMO</p><h3>没有真实数据？</h3><p class="helper-text">生成演示数据体验完整诊断流程。</p><button class="button ghost full" @click="demo">创建演示数据</button></article></aside></div></section></template>
