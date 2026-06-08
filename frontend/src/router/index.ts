import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'dashboard', component: () => import('@/views/DashboardView.vue') },
    { path: '/role', name: 'role', component: () => import('@/views/RoleView.vue') },
    { path: '/network', name: 'network', component: () => import('@/views/NetworkView.vue') },
    { path: '/theme', name: 'theme', component: () => import('@/views/ThemeView.vue') },
    { path: '/narrative', name: 'narrative', component: () => import('@/views/NarrativeView.vue') },
  ],
})

export default router
