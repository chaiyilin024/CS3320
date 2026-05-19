<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import ChartCard from '@/components/ChartCard.vue'
import { api } from '@/api/client'
import { useChart } from '@/composables/useChart'
import { useFilterStore } from '@/stores/filter'
import type { PlayThemes, ThemePatternsGlobal } from '@/types'

const store = useFilterStore()
const themes = ref<PlayThemes | null>(null)
const patterns = ref<ThemePatternsGlobal | null>(null)
const pieEl = ref<HTMLElement | null>(null)
const heatEl = ref<HTMLElement | null>(null)

async function load() {
  if (!store.scriptId) return
  themes.value = await api.playThemes(store.scriptId)
  try {
    patterns.value = await api.globalThemes()
  } catch {
    patterns.value = null
  }
}

onMounted(load)
watch(() => store.scriptId, load)

const pieOpt = computed(() => {
  const t = themes.value?.topics ?? []
  return {
    tooltip: { trigger: 'item' },
    series: [{
      type: 'pie',
      radius: '65%',
      data: t.map((x) => ({
        name: x.label,
        value: x.weight,
        topic_id: x.topic_id,
      })),
    }],
  }
})

const heatOpt = computed(() => {
  const p = patterns.value
  if (!p?.play_topic_matrix.length) return {}
  const labels = p.topic_labels.map((l) => l.label)
  const rows = p.play_topic_matrix
  return {
    tooltip: { position: 'top' },
    grid: { left: 100, right: 30, bottom: 80, top: 20 },
    xAxis: { type: 'category', data: labels, axisLabel: { rotate: 30 } },
    yAxis: { type: 'category', data: rows.map((r) => r.title ?? r.script_id) },
    visualMap: { min: 0, max: 0.5, calculable: true, orient: 'horizontal', bottom: 0 },
    series: [{
      type: 'heatmap',
      data: rows.flatMap((row, yi) =>
        row.weights.map((w, xi) => [xi, yi, w] as [number, number, number]),
      ),
    }],
  }
})

useChart(pieEl, () => pieOpt.value, [pieOpt])
useChart(heatEl, () => heatOpt.value, [heatOpt])

function selectTopic(id: number) {
  store.toggleTopic(id)
}
</script>

<template>
  <div class="page">
    <h2 class="page-title">任务三 · 主题分析</h2>
    <div v-if="!themes" class="loading">加载中…</div>
    <template v-else>
      <div class="grid-2">
        <ChartCard title="本剧主题构成">
          <div ref="pieEl" class="chart" />
        </ChartCard>
        <ChartCard title="跨剧主题热力">
          <div ref="heatEl" class="chart" />
        </ChartCard>
      </div>
      <div class="topics">
        <div
          v-for="t in themes.topics"
          :key="t.topic_id"
          class="topic-card"
          :class="{ active: store.selectedTopicIds.includes(t.topic_id) }"
          @click="selectTopic(t.topic_id)"
        >
          <h4>{{ t.label }}</h4>
          <p class="w">{{ (t.weight * 100).toFixed(1) }}%</p>
          <p class="kw">{{ t.keywords.slice(0, 8).join(' · ') }}</p>
        </div>
      </div>
      <ChartCard v-if="themes.representative_blocks?.length" title="代表片段">
        <ul class="snippets">
          <li v-for="(r, i) in themes.representative_blocks.slice(0, 8)" :key="i">
            <span class="tid">T{{ r.topic_id }}</span> {{ r.text_snippet }}
          </li>
        </ul>
      </ChartCard>
    </template>
  </div>
</template>

<style scoped>
.page-title { margin: 0 0 1rem; font-family: var(--font-serif); }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem; }
.chart { height: 300px; }
.topics { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 0.6rem; margin-bottom: 1rem; }
.topic-card {
  padding: 0.75rem;
  border: 1px solid var(--border);
  border-radius: 8px;
  cursor: pointer;
  background: var(--surface);
}
.topic-card.active { border-color: var(--accent-gold); background: #fff8e8; }
.topic-card h4 { margin: 0 0 0.25rem; font-size: 0.95rem; }
.w { margin: 0; font-weight: 600; color: var(--accent-red); }
.kw { margin: 0.35rem 0 0; font-size: 0.75rem; color: var(--text-muted); }
.snippets { margin: 0; padding-left: 1.2rem; font-size: 0.85rem; line-height: 1.6; }
.tid { color: var(--accent-gold); font-weight: 600; margin-right: 0.35rem; }
.loading { color: var(--text-muted); }
</style>
