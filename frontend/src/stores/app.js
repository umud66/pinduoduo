import { defineStore } from 'pinia'
import { listShops } from '@/api/shop.js'
import { listProviders } from '@/api/ai.js'

export const useAppStore = defineStore('app', {
  state: () => ({ shops: [], providers: [], selectedShopId: null, loading: false, globalError: '' }),
  getters: {
    currentShop: (state) => state.shops.find((item) => item.id === state.selectedShopId) || null,
    activeProvider: (state) => state.providers.find((item) => item.enabled) || null,
  },
  actions: {
    async refresh() {
      this.loading = true
      try {
        const [shops, providers] = await Promise.all([listShops(), listProviders()])
        this.shops = shops || []
        this.providers = providers || []
        const saved = Number(localStorage.getItem('pdd-selected-shop') || 0)
        if (!this.shops.some((item) => item.id === this.selectedShopId)) {
          this.selectedShopId = this.shops.some((item) => item.id === saved) ? saved : this.shops[0]?.id || null
        }
      } finally { this.loading = false }
    },
    selectShop(value) {
      this.selectedShopId = value ? Number(value) : null
      if (this.selectedShopId) localStorage.setItem('pdd-selected-shop', String(this.selectedShopId))
    },
  },
})
