import { nextTick, onMounted, onUnmounted, shallowRef, watch, type Ref } from 'vue'
import type { EChartsOption } from 'echarts'
import { echarts } from '@/utils/charts'

type ChartInstance = ReturnType<typeof echarts.init>

export function useChart(
  elRef: Ref<HTMLElement | null>,
  getOption: () => EChartsOption,
  deps: Ref<unknown>[] = [],
  onEvents?: Record<string, (params: unknown) => void>,
) {
  const chart = shallowRef<ChartInstance | null>(null)
  let eventsBound = false
  let resizeObserver: ResizeObserver | null = null

  function bindEvents() {
    const instance = chart.value
    if (!instance || !onEvents || eventsBound) return
    Object.entries(onEvents).forEach(([name, handler]) => {
      instance.on(name, handler as (p: unknown) => void)
    })
    eventsBound = true
  }

  function disposeChart() {
    chart.value?.dispose()
    chart.value = null
    eventsBound = false
  }

  function render() {
    const el = elRef.value
    if (!el || el.clientWidth === 0 || el.clientHeight === 0) return

    const boundEl = chart.value?.getDom?.() as HTMLElement | undefined
    if (chart.value && boundEl !== el) disposeChart()

    if (!chart.value) chart.value = echarts.init(el)
    chart.value.setOption(getOption(), { notMerge: true })
    chart.value.resize()
    bindEvents()
  }

  function scheduleRender() {
    void nextTick(() => {
      render()
      // First frame / after v-if remount, dimensions may not be ready yet
      requestAnimationFrame(() => {
        render()
        requestAnimationFrame(render)
      })
    })
  }

  function observeElement(el: HTMLElement | null) {
    resizeObserver?.disconnect()
    resizeObserver = null
    if (!el) return
    resizeObserver = new ResizeObserver(() => {
      const boundEl = chart.value?.getDom?.() as HTMLElement | undefined
      if (chart.value && boundEl !== el) disposeChart()
      if (!chart.value && el.clientWidth > 0 && el.clientHeight > 0) {
        render()
      } else {
        chart.value?.resize()
      }
    })
    resizeObserver.observe(el)
  }

  onMounted(() => {
    observeElement(elRef.value)
    scheduleRender()
    window.addEventListener('resize', scheduleRender)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', scheduleRender)
    resizeObserver?.disconnect()
    disposeChart()
  })

  watch(elRef, (el) => {
    if (!el) {
      disposeChart()
    } else {
      const boundEl = chart.value?.getDom?.() as HTMLElement | undefined
      if (chart.value && boundEl !== el) disposeChart()
    }
    observeElement(el)
    if (el) scheduleRender()
  })

  watch(deps, scheduleRender, { deep: true })

  return { chart, render: scheduleRender }
}
