import { defineStore } from 'pinia'
import { getSyncStatus } from '@/api/sync.js'

export const useSyncStore = defineStore('sync', {
  state: () => ({ status: null, timer: null, shopId: null }),
  actions: {
    async refresh(shopId) {
      if (!shopId) { this.status = null; return }
      this.status = await getSyncStatus(shopId)
    },
    startPolling(shopId) {
      this.stopPolling()
      this.shopId = shopId || null
      if (!this.shopId) return
      const tick = async () => {
        try { await this.refresh(this.shopId) } catch { /* page-level actions surface errors */ }
        const delay = this.status?.active ? 2200 : 15000
        this.timer = window.setTimeout(tick, delay)
      }
      tick()
    },
    stopPolling() { if (this.timer) window.clearTimeout(this.timer); this.timer = null },
  },
})
