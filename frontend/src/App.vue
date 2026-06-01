<script setup lang="ts">
import { onMounted } from 'vue'
import AppLayout from '@/components/AppLayout.vue'
import { useFilterStore } from '@/stores/filter'
import { useRoute, useRouter } from 'vue-router'

const store = useFilterStore()
const route = useRoute()
const router = useRouter()

onMounted(() => {
  const q = route.query.script
  if (typeof q === 'string' && q) store.setScriptId(q)
})

router.afterEach((to) => {
  if (store.scriptId && to.query.script !== store.scriptId) {
    router.replace({ ...to, query: { ...to.query, script: store.scriptId } })
  }
})
</script>

<template>
  <AppLayout />
</template>
