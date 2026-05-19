<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { api } from '@/api/client'
import { useFilterStore } from '@/stores/filter'
import type { CatalogPlay } from '@/types'

const store = useFilterStore()
const plays = ref<CatalogPlay[]>([])
const stats = ref({ plays: 0, chars: 0, blocks: 0 })

onMounted(async () => {
  const cat = await api.catalog()
  plays.value = cat.plays
  stats.value = {
    plays: cat.plays.length,
    chars: cat.plays.reduce((s, p) => s + (p.character_count ?? 0), 0),
    blocks: cat.plays.reduce((s, p) => s + (p.block_count ?? 0), 0),
  }
})

const tasks = [
  { path: '/role', title: '人物与行当', desc: '特征推断、行当分布' },
  { path: '/network', title: '人物关系网络', desc: '力导向图、网络指标' },
  { path: '/theme', title: '主题分析', desc: '主题构成、关键词、热力图' },
  { path: '/narrative', title: '叙事结构', desc: '情节阶段、节奏曲线' },
  { path: '/integrated', title: '综合探索', desc: '跨维度关联与洞察' },
]
</script>

<template>
  <div class="dashboard">
    <section class="hero">
      <h2>ChinaVis · 戏韵万象</h2>
      <p>基于预处理与分析 JSON 的京剧剧本多视图探索系统</p>
    </section>
    <div class="kpis">
      <div class="kpi"><span class="num">{{ stats.plays }}</span><span class="lbl">剧本</span></div>
      <div class="kpi"><span class="num">{{ stats.chars }}</span><span class="lbl">人物</span></div>
      <div class="kpi"><span class="num">{{ stats.blocks }}</span><span class="lbl">正文块</span></div>
    </div>
    <section class="tasks">
      <h3>分析任务</h3>
      <div class="grid">
        <RouterLink
          v-for="t in tasks"
          :key="t.path"
          :to="{ path: t.path, query: store.scriptId ? { script: store.scriptId } : {} }"
          class="task-card"
        >
          <h4>{{ t.title }}</h4>
          <p>{{ t.desc }}</p>
        </RouterLink>
      </div>
    </section>
    <section v-if="plays.length" class="play-list">
      <h3>剧本目录</h3>
      <table>
        <thead>
          <tr>
            <th>ID</th><th>剧名</th><th>集合</th><th>体裁</th><th>人物</th><th>块数</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="p in plays"
            :key="p.script_id"
            :class="{ active: p.script_id === store.scriptId }"
            @click="store.setScriptId(p.script_id)"
          >
            <td>{{ p.script_id }}</td>
            <td>{{ p.title }}</td>
            <td>{{ p.collection_name }}</td>
            <td>{{ p.tags?.genre_inferred ?? '—' }}</td>
            <td>{{ p.character_count }}</td>
            <td>{{ p.block_count }}</td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<style scoped>
.dashboard { display: flex; flex-direction: column; gap: 1.5rem; }
.hero h2 { margin: 0; font-family: var(--font-serif); font-size: 1.75rem; }
.hero p { color: var(--text-muted); margin: 0.35rem 0 0; }
.kpis { display: flex; gap: 1rem; flex-wrap: wrap; }
.kpi {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1rem 1.5rem;
  min-width: 100px;
  text-align: center;
}
.kpi .num { display: block; font-size: 1.75rem; font-weight: 700; color: var(--accent-red); }
.kpi .lbl { font-size: 0.85rem; color: var(--text-muted); }
.tasks h3, .play-list h3 { margin: 0 0 0.75rem; font-family: var(--font-serif); }
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 0.75rem;
}
.task-card {
  padding: 1rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  text-decoration: none;
  color: inherit;
  transition: border-color 0.15s, transform 0.15s;
}
.task-card:hover {
  border-color: var(--accent-gold);
  transform: translateY(-2px);
}
.task-card h4 { margin: 0 0 0.35rem; font-size: 1rem; }
.task-card p { margin: 0; font-size: 0.8rem; color: var(--text-muted); }
table { width: 100%; border-collapse: collapse; font-size: 0.9rem; background: var(--surface); border-radius: 10px; overflow: hidden; }
th, td { padding: 0.6rem 0.75rem; text-align: left; border-bottom: 1px solid var(--border); }
th { background: #faf6f0; font-weight: 600; }
tr { cursor: pointer; }
tr:hover { background: #fdf8f3; }
tr.active { background: #fff3e0; }
</style>
