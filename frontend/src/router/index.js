import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '@/views/DashboardView.vue'
import SkuDiagnosisView from '@/views/SkuDiagnosisView.vue'
import DataCenterView from '@/views/DataCenterView.vue'
import AiStudioView from '@/views/AiStudioView.vue'
import SettingsView from '@/views/SettingsView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/dashboard', name: 'dashboard', component: DashboardView, meta: { title: '经营总览', kicker: '店铺经营' } },
    { path: '/skus', name: 'skus', component: SkuDiagnosisView, meta: { title: 'SKU 诊断', kicker: '诊断中心' } },
    { path: '/data', name: 'data', component: DataCenterView, meta: { title: '数据中心', kicker: '数据接入' } },
    { path: '/ai', name: 'ai', component: AiStudioView, meta: { title: 'AI 工作台', kicker: 'AI 能力' } },
    { path: '/settings', name: 'settings', component: SettingsView, meta: { title: '设置', kicker: '系统配置' } },
  ],
})

export default router
