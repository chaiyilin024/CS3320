<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import ChartCard from '@/components/ChartCard.vue'
import { api } from '@/api/client'
import { useChart } from '@/composables/useChart'
import { useFilterStore } from '@/stores/filter'
import type { PlayIntegrated, PlayNetwork, PlayNarrative } from '@/types'

const store = useFilterStore()
const data = ref<PlayIntegrated | null>(null)
const network = ref<PlayNetwork | null>(null)
const narrative = ref<PlayNarrative | null>(null)
const heatEl = ref<HTMLElement | null>(null)
const stageEl = ref<HTMLElement | null>(null)
const miniGraphEl = ref<HTMLElement | null>(null)

async function load() {
  if (!store.scriptId) return
  const id = store.scriptId
  data.value = await api.playIntegrated(id)
  network.value = await api.playNetwork(id)
  narrative.value = await api.playNarrative(id)
}

onMounted(load)
watch(() => store.scriptId, load)

const heatOpt = computed(() => {
  const cells = data.value?.character_topic_matrix ?? []
  const chars = [...new Set(cells.map((c) => c.character_name ?? c.character_id))]
  const topics = [...new Set(cells.map((c) => c.topic_label ?? `T${c.topic_id}`))]
  return {
    tooltip: {},
    grid: { left: 90, right: 20, bottom: 60, top: 20 },
    xAxis: { type: 'category', data: topics, axisLabel: { rotate: 25 } },
    yAxis: { type: 'category', data: chars },
    visualMap: { min: 0, max: 1, calculable: true, orient: 'horizontal', bottom: 0 },
    series: [{
      type: 'heatmap',
      data: cells.map((c) => [
        topics.indexOf(c.topic_label ?? `T${c.topic_id}`),
        chars.indexOf(c.character_name ?? c.character_id),
        c.strength,
      ]),
    }],
  }
})

const stageOpt = computed(() => {
  const snaps = data.value?.stage_network_snapshots ?? []
  return {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: snaps.map((s) => s.stage) },
    yAxis: { type: 'value' },
    series: [{ type: 'line', data: snaps.map((s) => s.edge_density), areaStyle: { opacity: 0.2 } }],
  }
})

const miniGraphOpt = computed(() => {
  const n = network.value
  if (!n) return {}
  return {
    series: [{
      type: 'graph',
      layout: 'force',
      roam: false,
      symbolSize: 18,
      data: n.nodes.slice(0, 12).map((node) => ({
        id: node.id,
        name: node.name,
        itemStyle: { color: store.selectedCharacterIds.includes(node.id) ? '#c62828' : '#8b4513' },
      })),
      links: n.links.slice(0, 20).map((l) => ({ source: l.source, target: l.target })),
      force: { repulsion: 120 },
    }],
  }
})

useChart(heatEl, () => heatOpt.value, [heatOpt])
useChart(stageEl, () => stageOpt.value, [stageOpt])
useChart(miniGraphEl, () => miniGraphOpt.value, [miniGraphOpt, () => store.selectedCharacterIds])
</script>

<template>
  <div class="page">
    <h2 class="page-title">任务五 · 综合探索</h2>
    <div v-if="!data" class="loading">加载中…</div>
    <template v-else>
      <section class="insights">
        <article v-for="(line, i) in data.summary_insights" :key="i" class="insight">
          {{ line }}
        </article>
      </section>
      <div class="grid-3">
        <ChartCard title="人物 × 主题">
          <div ref="heatEl" class="chart" />
        </ChartCard>
        <ChartCard title="阶段网络密度">
          <div ref="stageEl" class="chart" />
        </ChartCard>
        <ChartCard title="关系网络缩略">
          <div ref="miniGraphEl" class="chart" />
        </ChartCard>
      </div>
      <ChartCard v-if="data.correlations?.length" title="关联明细">
        <table class="table">
          <thead><tr><th>类型</th><th>强度</th><th>说明</th></tr></thead>
          <tbody>
            <tr v-for="(c, i) in data.correlations.slice(0, 12)" :key="i">
              <td>{{ c.type }}</td>
              <td>{{ ((c.strength as number) * 100).toFixed(0) }}%</td>
              <td>{{ c.evidence }}</td>
            </tr>
          </tbody>
        </table>
      </ChartCard>
    </template>
  </div>
</template>

<style scoped>
.page-title { margin: 0 0 1rem; font-family: var(--font-serif); }
.insights { display: flex; flex-direction: column; gap: 0.5rem; margin-bottom: 1rem; }
.insight {
  padding: 0.75rem 1rem;
  background: linear-gradient(90deg, #fff8e8, var(--surface));
  border-left: 4px solid var(--accent-gold);
  border-radius: 0 8px 8px 0;
  font-size: 0.92rem;
  line-height: 1.5;
}
.grid-3 {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin-bottom: 1rem;
}
@media (max-width: 1000px) { .grid-3 { grid-template-columns: 1fr; } }
.chart { height: 260px; }
.table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
th, td { padding: 0.45rem; border-bottom: 1px solid var(--border); text-align: left; }
.loading { color: var(--text-muted); }
</style>
