<script setup lang="ts">
defineProps<{ title: string; subtitle?: string }>()
</script>

<template>
  <section class="chart-card">
    <header v-if="title" class="head">
      <h3>{{ title }}</h3>
      <p v-if="subtitle" class="sub">{{ subtitle }}</p>
    </header>
    <div class="body">
      <slot />
    </div>
  </section>
</template>

<style scoped>
.chart-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  box-shadow: var(--shadow);
}
.head {
  padding: 0.85rem 1rem 0;
}
.head h3 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  font-family: var(--font-serif);
}
.sub {
  margin: 0.25rem 0 0;
  font-size: 0.8rem;
  color: var(--text-muted);
}
.body {
  padding: 0.5rem 0.75rem 0.75rem;
  min-height: 120px;
}
</style>
