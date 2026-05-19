<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import ChartCard from '@/components/ChartCard.vue'
import { api } from '@/api/client'
import { useChart } from '@/composables/useChart'
import { useFilterStore } from '@/stores/filter'
import { hangdangColor } from '@/utils/charts'
import type { PlayRole, RoleAnalysisGlobal } from '@/types'

const store = useFilterStore()
const role = ref<PlayRole | null>(null)
const globalRole = ref<RoleAnalysisGlobal | null>(null)
const pieEl = ref<HTMLElement | null>(null)
const heatEl = ref<HTMLElement | null>(null)

async function load() {
  if (!store.scriptId) return
  role.value = await api.playRole(store.scriptId)
  try {
    globalRole.value = await api.globalRole()
  } catch {
    globalRole.value = null
  }
}

onMounted(load)
watch(() => store.scriptId, load)

const pieOpt = computed(() => {
  const d = role.value?.hangdang_distribution ?? {}
  return {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: Object.entries(d).map(([name, value]) => ({
        name,
        value,
        itemStyle: { color: hangdangColor(name) },
      })),
    }],
  }
})

const heatOpt = computed(() => {
  const cells = globalRole.value?.global_feature_hangdang_matrix ?? []
  const hangdangs = [...new Set(cells.map((c) => c.hangdang))]
  const features = [...new Set(cells.map((c) => c.feature))].slice(0, 12)
  const data: [number, number, number][] = []
  cells.forEach((c) => {
    const xi = features.indexOf(c.feature)
    const yi = hangdangs.indexOf(c.hangdang)
    if (xi >= 0 && yi >= 0) data.push([xi, yi, c.count])
  })
  return {
    tooltip: { position: 'top' },
    grid: { left: 120, right: 20, bottom: 60, top: 20 },
    xAxis: { type: 'category', data: features, axisLabel: { rotate: 35, fontSize: 10 } },
    yAxis: { type: 'category', data: hangdangs },
    visualMap: { min: 0, max: Math.max(...data.map((d) => d[2]), 1), calculable: true, orient: 'horizontal', left: 'center', bottom: 0 },
    series: [{ type: 'heatmap', data, label: { show: false } }],
  }
})

useChart(pieEl, () => pieOpt.value, [pieOpt])
useChart(heatEl, () => heatOpt.value, [heatOpt])
</script>

<template>
  <div class="page">
    <h2 class="page-title">任务一 · 人物与行当</h2>
    <div v-if="!role" class="loading">加载中…</div>
    <template v-else>
      <div class="grid-2">
        <ChartCard title="本剧行当分布">
          <div ref="pieEl" class="chart" />
        </ChartCard>
        <ChartCard title="全局特征×行当" subtitle="热力图">
          <div ref="heatEl" class="chart" />
        </ChartCard>
      </div>
      <ChartCard title="人物明细">
        <table class="table">
          <thead>
            <tr>
              <th>姓名</th><th>标注</th><th>推断</th><th>最终</th><th>置信度</th><th>特征</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="c in role.characters"
              :key="c.character_id"
              :class="{ hl: store.selectedCharacterIds.includes(c.character_id) }"
              @click="store.toggleCharacter(c.character_id)"
            >
              <td>{{ c.name }}</td>
              <td>{{ c.hangdang_labeled ?? '—' }}</td>
              <td>{{ c.hangdang_inferred ?? '—' }}</td>
              <td><span class="tag" :style="{ background: hangdangColor(c.hangdang_final) }">{{ c.hangdang_final }}</span></td>
              <td>{{ (c.confidence * 100).toFixed(0) }}%</td>
              <td class="feat">{{ (c.top_features ?? []).join(' · ') }}</td>
            </tr>
          </tbody>
        </table>
      </ChartCard>
    </template>
  </div>
</template>

<style scoped>
.page-title { margin: 0 0 1rem; font-family: var(--font-serif); }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem; }
@media (max-width: 900px) { .grid-2 { grid-template-columns: 1fr; } }
.chart { height: 320px; }
.table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
th, td { padding: 0.5rem; border-bottom: 1px solid var(--border); text-align: left; }
tr { cursor: pointer; }
tr.hl, tr:hover { background: #fff8e8; }
.tag { color: #fff; padding: 0.15rem 0.5rem; border-radius: 4px; font-size: 0.8rem; }
.feat { font-size: 0.75rem; color: var(--text-muted); max-width: 280px; }
.loading { color: var(--text-muted); }
</style>
