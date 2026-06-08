import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

export const useFilterStore = defineStore('filter', () => {
  const scriptId = ref<string | null>('01001012')
  const collectionId = ref<string | null>(null)
  const genre = ref<string | null>(null)
  const selectedCharacterIds = ref<string[]>([])
  const selectedTopicIds = ref<number[]>([])
  const narrativeBlockRange = ref<[number, number] | null>(null)
  const filterHangdang = ref<string | null>(null)
  const catalogDemo = ref(false)
  const catalogDemoNote = ref<string | null>(null)

  function setCatalogMeta(demo: boolean, note?: string | null) {
    catalogDemo.value = demo
    catalogDemoNote.value = note ?? null
  }

  function setScriptId(id: string | null) {
    scriptId.value = id
  }

  function setGenre(g: string | null) {
    genre.value = g
  }

  function setCollectionId(id: string | null) {
    collectionId.value = id
  }

  function setNarrativeBlockRange(range: [number, number] | null) {
    narrativeBlockRange.value = range
  }

  function setFilterHangdang(hd: string | null) {
    filterHangdang.value = hd
  }

  function clearGlobalFilters() {
    genre.value = null
    collectionId.value = null
    filterHangdang.value = null
  }

  function toggleCharacter(id: string) {
    const i = selectedCharacterIds.value.indexOf(id)
    if (i >= 0) selectedCharacterIds.value.splice(i, 1)
    else selectedCharacterIds.value = [id]
  }

  function toggleTopic(id: number) {
    const i = selectedTopicIds.value.indexOf(id)
    if (i >= 0) selectedTopicIds.value.splice(i, 1)
    else selectedTopicIds.value = [id]
  }

  function clearSelection() {
    selectedCharacterIds.value = []
    selectedTopicIds.value = []
    narrativeBlockRange.value = null
  }

  return {
    scriptId,
    collectionId,
    genre,
    selectedCharacterIds,
    selectedTopicIds,
    narrativeBlockRange,
    filterHangdang,
    catalogDemo,
    catalogDemoNote,
    setScriptId,
    setGenre,
    setCollectionId,
    setNarrativeBlockRange,
    setFilterHangdang,
    setCatalogMeta,
    clearGlobalFilters,
    toggleCharacter,
    toggleTopic,
    clearSelection,
  }
})

/** 将 scriptId 同步到 URL query */
export function useScriptQuerySync() {
  const store = useFilterStore()
  const route = useRoute()
  const router = useRouter()

  if (route.query.script && typeof route.query.script === 'string') {
    store.setScriptId(route.query.script)
  }

  watch(
    () => store.scriptId,
    (id) => {
      if (id && route.query.script !== id) {
        router.replace({ query: { ...route.query, script: id } })
      }
    },
  )
}
