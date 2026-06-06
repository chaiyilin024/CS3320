<script setup lang="ts">
import { RouterLink, RouterView, useRoute } from 'vue-router'
import GlobalFilterBar from './GlobalFilterBar.vue'
import PlaySelector from './PlaySelector.vue'
import { useFilterStore } from '@/stores/filter'

const route = useRoute()
const store = useFilterStore()

const nav = [
  { path: '/', label: '总览' },
  { path: '/role', label: '行当' },
  { path: '/network', label: '网络' },
  { path: '/theme', label: '主题' },
  { path: '/narrative', label: '叙事' },
  { path: '/integrated', label: '综合' },
]
</script>

<template>
  <div class="app">
    <header class="header">
      <div class="brand">
        <h1>戏韵万象</h1>
        <span class="tag">京剧剧本可视化</span>
      </div>
      <nav class="nav">
        <RouterLink
          v-for="item in nav"
          :key="item.path"
          :to="{ path: item.path, query: store.scriptId ? { script: store.scriptId } : {} }"
          class="nav-link"
          :class="{ active: route.path === item.path }"
        >
          {{ item.label }}
        </RouterLink>
      </nav>
      <GlobalFilterBar />
      <PlaySelector />
    </header>
    <main class="main">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
.header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 1rem 1.5rem;
  padding: 0.85rem 1.5rem;
  background: linear-gradient(135deg, #1a0f0a 0%, #3d1810 50%, #1a0f0a 100%);
  border-bottom: 3px solid var(--accent-gold);
  color: #f5e6d3;
}
.brand h1 {
  margin: 0;
  font-family: var(--font-serif);
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: 0.08em;
}
.tag {
  font-size: 0.75rem;
  opacity: 0.75;
  margin-left: 0.5rem;
}
.nav {
  display: flex;
  gap: 0.35rem;
  flex: 1;
}
.nav-link {
  padding: 0.4rem 0.85rem;
  border-radius: 6px;
  color: #e8d5c4;
  text-decoration: none;
  font-size: 0.9rem;
  transition: background 0.15s;
}
.nav-link:hover {
  background: rgba(255, 255, 255, 0.1);
}
.nav-link.active {
  background: var(--accent-gold);
  color: #1a0f0a;
  font-weight: 600;
}
.main {
  flex: 1;
  padding: 1.25rem 1.5rem 2rem;
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
  box-sizing: border-box;
}
</style>
