<script setup lang="ts">
export type SectionTab = { id: string; label: string }

defineProps<{
  tabs: SectionTab[]
}>()

const active = defineModel<string>({ required: true })

const emit = defineEmits<{ change: [id: string] }>()

function pick(id: string) {
  if (active.value === id) return
  active.value = id
  emit('change', id)
}
</script>

<template>
  <nav class="page-tabs" role="tablist">
    <button
      v-for="tab in tabs"
      :key="tab.id"
      type="button"
      role="tab"
      class="page-tab"
      :class="{ active: active === tab.id }"
      :aria-selected="active === tab.id"
      @click="pick(tab.id)"
    >
      {{ tab.label }}
    </button>
  </nav>
</template>
