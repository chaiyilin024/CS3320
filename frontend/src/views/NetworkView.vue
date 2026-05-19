<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import ChartCard from '@/components/ChartCard.vue'
import { api } from '@/api/client'
import { useChart } from '@/composables/useChart'
import { useFilterStore } from '@/stores/filter'
import { hangdangColor } from '@/utils/charts'
import type { PlayNetwork } from '@/types'

const store = useFilterStore()
const net = ref<PlayNetwork | null>(null)
const graphEl = ref<HTMLElement | null>(null)
const barEl = ref<HTMLElement | null>(null)

async function load() {
  if (!store.scriptId) return
  net.value = await api.playNetwork(store.scriptId)
}

onMounted(load)
watch(() => store.scriptId, load)

const graphOpt = computed(() => {
  const n = net.value
  if (!n) return {}
  const sel = new Set(store.selectedCharacterIds)
  return {
    tooltip: {},
    series: [{
      type: 'graph',
      layout: 'force',
      roam: true,
      data: n.nodes.map((node) => ({
        id: node.id,
        name: node.name,
        symbolSize: 12 + node.degree * 2,
        itemStyle: {
          color: hangdangColor(node.hangdang),
          borderWidth: sel.has(node.id) ? 3 : 0,
          borderColor: '#c62828',
        },
        label: { show: true, fontSize: 11 },
      })),
      links: n.links.map((l) => ({
        source: l.source,
        target: l.target,
        lineStyle: { width: Math.min(8, 1 + l.weight / 10), opacity: 0.6 },
      })),
      force: { repulsion: 200, edgeLength: [80, 160] },
    }],
  }
})

const barOpt = computed(() => {
  const nodes = [...(net.value?.nodes ?? [])].sort((a, b) => b.degree - a.degree).slice(0, 8)
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 80, right: 20, top: 20, bottom: 30 },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: nodes.map((n) => n.name) },
    series: [{ type: 'bar', data: nodes.map((n) => n.degree), itemStyle: { color: '#8b2500' } }],
  }
})

useChart(graphEl, () => graphOpt.value, [graphOpt, () => store.selectedCharacterIds])
useChart(barEl, () => barOpt.value, [barOpt])

</script>

<template>
  <div class="page">
    <h2 class="page-title">任务二 · 人物关系网络</h2>
    <div v-if="net" class="metrics">
      <span>节点 {{ net.metrics.node_count }}</span>
      <span>边 {{ net.metrics.edge_count }}</span>
      <span>密度 {{ net.metrics.density.toFixed(3) }}</span>
      <span>聚类 {{ (net.metrics.avg_clustering ?? 0).toFixed(3) }}</span>
    </div>
    <div class="grid-2">
      <ChartCard title="关系力导向图" subtitle="点击节点高亮人物">
        <div ref="graphEl" class="chart tall" />
      </ChartCard>
      <ChartCard title="核心人物（加权度）">
        <div ref="barEl" class="chart" />
      </ChartCard>
    </div>
  </div>
</template>

<style scoped>
.page-title { margin: 0 0 0.75rem; font-family: var(--font-serif); }
.metrics { display: flex; gap: 1.25rem; margin-bottom: 1rem; font-size: 0.9rem; color: var(--text-muted); }
.grid-2 { display: grid; grid-template-columns: 1.2fr 0.8fr; gap: 1rem; }
@media (max-width: 900px) { .grid-2 { grid-template-columns: 1fr; } }
.chart { height: 300px; }
.chart.tall { height: 420px; }
</style>
