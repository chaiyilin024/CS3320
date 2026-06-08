<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '@/api/client'
import { useFilterStore } from '@/stores/filter'
import { filterCatalogPlays } from '@/utils/catalogFilter'
import type { CatalogPlay } from '@/types'

const store = useFilterStore()
const plays = ref<CatalogPlay[]>([])
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    const cat = await api.catalog()
    plays.value = cat.plays
    store.setCatalogMeta(!!cat.demo, cat.demo_note)
    if (!store.scriptId && plays.value[0]) {
      store.setScriptId(plays.value[0].script_id)
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : '加载目录失败'
  } finally {
    loading.value = false
  }
})

const filteredPlays = computed(() =>
  filterCatalogPlays(plays.value, {
    genre: store.genre,
    collectionId: store.collectionId,
  }),
)

const current = computed(() =>
  filteredPlays.value.find((p) => p.script_id === store.scriptId)
    ?? plays.value.find((p) => p.script_id === store.scriptId),
)

watch(filteredPlays, (list) => {
  if (!list.length) return
  if (!store.scriptId || !list.some((p) => p.script_id === store.scriptId)) {
    store.setScriptId(list[0].script_id)
  }
})
</script>

<template>
  <div class="play-selector">
    <label class="label">当前剧本</label>
    <select
      v-if="!loading && plays.length"
      :value="store.scriptId ?? ''"
      class="select"
      @change="store.setScriptId(($event.target as HTMLSelectElement).value)"
    >
      <option v-for="p in filteredPlays" :key="p.script_id" :value="p.script_id">
        {{ p.title }}（{{ p.script_id }}）
      </option>
    </select>
    <span v-else-if="loading" class="hint">加载中…</span>
    <span v-else class="hint error">{{ error || '无剧本数据，请运行 npm run prepare-data' }}</span>
    <span v-if="current" class="meta">
      {{ current.collection_name }} · {{ current.tags?.genre_inferred ?? '未知体裁' }}
    </span>
  </div>
</template>

<style scoped>
.play-selector {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.label {
  font-size: 0.85rem;
  color: var(--text-muted);
}
.select {
  min-width: 220px;
  padding: 0.45rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--surface);
  color: var(--text);
  font-family: inherit;
}
.meta {
  font-size: 0.8rem;
  color: var(--text-muted);
}
.hint {
  font-size: 0.85rem;
  color: var(--text-muted);
}
.error {
  color: var(--accent-red);
}
</style>
