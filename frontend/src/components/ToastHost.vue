<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
const items = ref([])
function pushToast(event) {
  const item = { id: Date.now() + Math.random(), message: event.detail?.message || '', type: event.detail?.type || '' }
  items.value.push(item)
  window.setTimeout(() => { items.value = items.value.filter((x) => x.id !== item.id) }, 4200)
}
onMounted(() => window.addEventListener('pdd:toast', pushToast))
onBeforeUnmount(() => window.removeEventListener('pdd:toast', pushToast))
</script>
<template><div class="toast-stack"><div v-for="item in items" :key="item.id" class="toast" :class="item.type">{{ item.message }}</div></div></template>
