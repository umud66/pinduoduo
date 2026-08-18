export const state = { shops: [], providers: [], selectedShopId: null, currentPage: "dashboard" };

export function selectShop(shopId) {
  state.selectedShopId = shopId ? Number(shopId) : null;
  if (state.selectedShopId) localStorage.setItem("pdd-selected-shop", String(state.selectedShopId));
}

export function hydrateShops(shops) {
  state.shops = shops;
  const saved = Number(localStorage.getItem("pdd-selected-shop") || 0);
  if (!state.selectedShopId || !shops.some((shop) => shop.id === state.selectedShopId)) {
    selectShop(shops.some((shop) => shop.id === saved) ? saved : shops[0]?.id || null);
  }
}
