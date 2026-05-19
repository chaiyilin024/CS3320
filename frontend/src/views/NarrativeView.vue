<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import ChartCard from '@/components/ChartCard.vue'
import { api } from '@/api/client'
import { useChart } from '@/composables/useChart'
import { useFilterStore } from '@/stores/filter'
import type { PlayNarrative } from '@/types'

const store = useFilterStore()
const narrative = ref<PlayNarrative | null>(null)
const lineEl = ref<HTMLElement | null>(null)
const perfEl = ref<HTMLElement | null>(null)

async function load() {
  if (!store.scriptId) return
  narrative.value = await api.playNarrative(store.scriptId)
}

onMounted(load)
watch(() => store.scriptId, load)

const lineOpt = computed(() => {
  const s = narrative.value?.rhythm_series ?? []
  const x = s.map((p) => p.block_index)
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['对白密度', '唱段占比', '情感', '张力'], bottom: 0 },
    grid: { left: 50, right: 20, top: 30, bottom: 50 },
    xAxis: { type: 'category', data: x, name: 'block' },
    yAxis: { type: 'value', max: 1 },
    series: [
      { name: '对白密度', type: 'line', data: s.map((p) => p.dialogue_density), smooth: true, showSymbol: false },
      { name: '唱段占比', type: 'line', data: s.map((p) => p.aria_ratio), smooth: true, showSymbol: false },
      { name: '情感', type: 'line', data: s.map((p) => p.emotion_score), smooth: true, showSymbol: false },
      { name: '张力', type: 'line', data: s.map((p) => p.tension_score), smooth: true, showSymbol: false },
    ],
  }
})

const perfOpt = computed(() => {
  const d = narrative.value?.performance_mark_distribution ?? {}
  return {
    tooltip: {},
    xAxis: { type: 'category', data: Object.keys(d) },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: Object.values(d), itemStyle: { color: '#5d4037' } }],
  }
})

useChart(lineEl, () => lineOpt.value, [lineOpt])
useChart(perfEl, () => perfOpt.value, [perfOpt])

function pickStage(range: [number, number]) {
  store.narrativeBlockRange = range
}
</script>

<template>
  <div class="page">
    <h2 class="page-title">任务四 · 叙事结构</h2>
    <div v-if="!narrative" class="loading">加载中…</div>
    <template v-else>
      <div class="stages">
        <button
          v-for="st in narrative.plot_stages"
          :key="st.stage + st.block_range.join()"
          class="stage-btn"
          :class="{ active: store.narrativeBlockRange?.[0] === st.block_range[0] }"
          @click="pickStage(st.block_range)"
        >
          <strong>{{ st.stage }}</strong>
          <span>{{ st.label }}</span>
          <small>block {{ st.block_range[0] }}–{{ st.block_range[1] }}</small>
        </button>
      </div>
      <ChartCard title="节奏曲线" subtitle="沿 block_index 的叙事节奏">
        <div ref="lineEl" class="chart tall" />
      </ChartCard>
      <ChartCard title="唱念做打分布">
        <div ref="perfEl" class="chart" />
      </ChartCard>
    </template>
  </div>
</template>

<style scoped>
.page-title { margin: 0 0 1rem; font-family: var(--font-serif); }
.stages { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1rem; }
.stage-btn {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface);
  cursor: pointer;
  font-size: 0.8rem;
}
.stage-btn.active { border-color: var(--accent-red); background: #ffebee; }
.stage-btn strong { font-size: 0.95rem; }
.stage-btn small { color: var(--text-muted); margin-top: 0.2rem; }
.chart { height: 280px; }
.chart.tall { height: 360px; }
.loading { color: var(--text-muted); }
</style>
