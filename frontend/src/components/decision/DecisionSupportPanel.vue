<script setup>
import ActionPriorityCard from './ActionPriorityCard.vue'
import ChangePointPanel from './ChangePointPanel.vue'
import StructureShiftPanel from './StructureShiftPanel.vue'
defineProps({ data: { type: Object, default: null } })
</script>

<template>
  <section v-if="data" class="decision-support-stack">
    <div v-if="data.summary?.length" class="decision-summary card compact">
      <p class="section-kicker">DECISION SUPPORT</p>
      <strong v-for="line in data.summary" :key="line">{{ line }}</strong>
    </div>
    <ActionPriorityCard :priority="data.action_priority" />
    <div class="decision-two-column">
      <ChangePointPanel :data="data.change_points" />
      <StructureShiftPanel :data="data.structure_shift" />
    </div>
  </section>
</template>

<style src="../../styles/decision-support.css"></style>
