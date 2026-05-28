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


const rolePieEl = ref<HTMLElement | null>(null)
const networkEl = ref<HTMLElement | null>(null)
const narrativeEl = ref<HTMLElement | null>(null)

/**
 * 核心按需加载管线：完全复用组员封装的 api 客户端
 * 每次切换剧本时，只拉取当前剧本对应的 3 个精简轻量 JSON 分片
 */
async function loadDashboardData() {
  if (!store.scriptId) return
  const id = store.scriptId
  
  // 并发请求后端正式产物，用完即释放，绝不盲读几千个
  const [resData, resNetwork, resNarrative] = await Promise.all([
    api.playIntegrated(id),
    api.playNetwork(id),
    api.playNarrative(id)
  ])
  
  data.value = resData
  network.value = resNetwork
  narrative.value = resNarrative
}

onMounted(loadDashboardData)
watch(() => store.scriptId, loadDashboardData)

/**
 * 任务一：行当结构特征推断比例 (ECharts 极简数据流驱动)
 */
const rolePieOpt = computed(() => {
  const nodes = network.value?.nodes ?? []
  
  // 运行时动态统计当前剧本的行当分布
  const counts = nodes.reduce((acc: Record<string, number>, node: any) => {
    const hd = node.hangdang || '未推断'
    acc[hd] = (acc[hd] || 0) + 1
    return acc;
  }, {})

  const pieData = Object.keys(counts).map(key => ({
    name: key,
    value: counts[key]
  }))

  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c}人 ({d}%)' },
    legend: { orient: 'vertical', left: 'left', textStyle: { color: '#ccc' } },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      avoidLabelOverlap: false,
      itemStyle: { borderRadius: 6 },
      label: { show: true, color: '#fff' },
      data: pieData
    }]
  }
})

/**
 * 任务二：人物互动网络演化 (完全契合组员现有的关系网高亮逻辑)
 */
const networkOpt = computed(() => {
  const n = network.value
  if (!n) return {}
  
  return {
    tooltip: {},
    series: [{
      type: 'graph',
      layout: 'force',
      roam: true,
      label: { show: true, position: 'bottom', color: '#fff' },
      symbolSize: (value: number, params: any) => {
        // 根据台词密度或权重动态缩放节点大小
        return Math.log(params.data.line_count || 10) * 5 + 10
      },
      data: n.nodes.map((node) => ({
        id: node.id,
        name: node.name,
        line_count: node.line_count,
        // 如果当前节点被选中，高亮显示为亮金色，否则保持古典棕
        itemStyle: { 
          color: store.selectedCharacterIds.includes(node.id) ? 'var(--accent-gold, #dfb96c)' : '#8b4513' 
        },
      })),
      links: n.links.map((l) => ({
        source: l.source,
        target: l.target,
        lineStyle: { width: Math.min(l.weight || 1, 5), opacity: 0.6 }
      })),
      force: { repulsion: 200, edgeLength: 100 },
    }],
  }
})

/**
 * 任务四：剧情演化与情感冲突浓度时序流
 */
const narrativeOpt = computed(() => {
  const snaps = data.value?.stage_network_snapshots ?? []
  return {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: snaps.map((s) => s.stage), axisLabel: { color: '#ccc' } },
    yAxis: { type: 'value', axisLabel: { color: '#ccc' } },
    series: [{ 
      name: '情感波动强度',
      type: 'line', 
      smooth: true,
      data: snaps.map((s) => s.edge_density * 100), // 借用网络密度衍生情感浓度
      lineStyle: { width: 3, color: '#dfb96c' },
      areaStyle: { opacity: 0.1 }
    }],
  }
})

// 4. 直接使用组员编写的专属图表注册钩子，自动实现图表自适应和内存释放
useChart(rolePieEl, () => rolePieOpt.value, [rolePieOpt])
useChart(networkEl, () => networkOpt.value, [networkOpt, () => store.selectedCharacterIds])
useChart(narrativeEl, () => narrativeOpt.value, [narrativeOpt])
</script>

<template>
  <div class="page">
    <!-- 头部横幅联动状态反馈 -->
    <header class="dashboard-banner">
      <h2 class="page-title">任务五 · 前端多维联调看板</h2>
      <div class="badge-group">
        <span class="badge">当前剧本ID: {{ store.scriptId || '未选择' }}</span>
        <span v-if="store.selectedCharacterIds.length" class="badge active">
          焦点角色ID: {{ store.selectedCharacterIds.join(', ') }}
        </span>
      </div>
    </header>

    <div v-if="!data" class="loading">正在按需加载当前剧本工件...</div>
    
    <template v-else>
      <!-- 上部双维并列看板 -->
      <div class="grid-2">
        <ChartCard title="任务一 · 行当自动推断结构分布">
          <div ref="rolePieEl" class="chart" />
        </ChartCard>
        
        <ChartCard title="任务二 · 人物互动关系网络 (动态高亮)">
          <div ref="networkEl" class="chart" />
        </ChartCard>
      </div>

      <!-- 下部时序故事演化大图 -->
      <ChartCard title="任务四 · 剧情块结构演化与情感特征时序走势">
        <div ref="narrativeEl" class="long-chart" />
      </ChartCard>
    </template>
  </div>
</template>

<style scoped>
.dashboard-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
}
.page-title { margin: 0; font-family: var(--font-serif); }
.badge-group { display: flex; gap: 0.5rem; }
.badge {
  padding: 0.25rem 0.75rem;
  background: var(--surface, #2c2c2c);
  border: 1px solid var(--border, #333);
  border-radius: 4px;
  font-size: 0.85rem;
  color: var(--text-muted, #aaa);
}
.badge.active {
  background: #dfb96c;
  color: #111;
  border-color: #dfb96c;
  font-weight: bold;
}
.grid-2 {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
  margin-bottom: 1rem;
}
@media (max-width: 850px) { .grid-2 { grid-template-columns: 1fr; } }
.chart { height: 300px; }
.long-chart { height: 350px; }
.loading { color: var(--text-muted); padding: 2rem 0; text-align: center; }
</style>
