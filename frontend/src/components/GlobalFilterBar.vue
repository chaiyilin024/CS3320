<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '@/api/client'
import { useFilterStore } from '@/stores/filter'
import { filterCatalogPlays, uniqueCollections, uniqueGenres } from '@/utils/catalogFilter'
import type { CatalogPlay } from '@/types'

const store = useFilterStore()
const plays = ref<CatalogPlay[]>([])

onMounted(async () => {
  try {
    const cat = await api.catalog()
    plays.value = cat.plays
  } catch {
    plays.value = []
  }
})

const genres = computed(() => uniqueGenres(plays.value))
const collections = computed(() => uniqueCollections(plays.value))
const filteredCount = computed(() =>
  filterCatalogPlays(plays.value, {
    genre: store.genre,
    collectionId: store.collectionId,
  }).length,
)

const hasFilter = computed(() => !!(store.genre || store.collectionId))
</script>

<template>
  <div class="filter-bar">
    <label class="fld">
      <span>体裁</span>
      <select
        :value="store.genre ?? ''"
        class="sel"
        @change="store.setGenre(($event.target as HTMLSelectElement).value || null)"
      >
        <option value="">全部体裁</option>
        <option v-for="g in genres" :key="g" :value="g">{{ g }}</option>
      </select>
    </label>
    <label class="fld">
      <span>集合</span>
      <select
        :value="store.collectionId ?? ''"
        class="sel"
        @change="store.setCollectionId(($event.target as HTMLSelectElement).value || null)"
      >
        <option value="">全部集合</option>
        <option v-for="c in collections" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>
    </label>
    <span v-if="hasFilter" class="count">{{ filteredCount }} 部剧本</span>
    <button v-if="hasFilter" type="button" class="clear" @click="store.clearGlobalFilters()">
      清除筛选
    </button>
  </div>
</template>

<style scoped>
.filter-bar {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  flex-wrap: wrap;
  padding: 0.5rem 0.75rem;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
}
.fld {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.78rem;
  color: #d4c4b0;
}
.sel {
  padding: 0.3rem 0.5rem;
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 5px;
  background: rgba(0, 0, 0, 0.25);
  color: #f5e6d3;
  font-size: 0.8rem;
  max-width: 140px;
}
.count {
  font-size: 0.75rem;
  color: #c9a227;
}
.clear {
  padding: 0.25rem 0.55rem;
  border: 1px solid rgba(201, 162, 39, 0.5);
  border-radius: 5px;
  background: transparent;
  color: #c9a227;
  font-size: 0.75rem;
  cursor: pointer;
}
.clear:hover {
  background: rgba(201, 162, 39, 0.15);
}
</style>
