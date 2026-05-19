import { onMounted, onUnmounted, ref, shallowRef, watch, type Ref } from 'vue'
import type { ECharts, EChartsOption } from 'echarts'
import { echarts } from '@/utils/charts'

export function useChart(
  elRef: Ref<HTMLElement | null>,
  getOption: () => EChartsOption,
  deps: Ref<unknown>[] = [],
) {
  const chart = shallowRef<ECharts | null>(null)

  function render() {
    if (!elRef.value) return
    if (!chart.value) chart.value = echarts.init(elRef.value)
    chart.value.setOption(getOption(), { notMerge: true })
  }

  onMounted(() => {
    render()
    window.addEventListener('resize', render)
  })

  onUnmounted(() => {
    window.removeEventListener('resize', render)
    chart.value?.dispose()
  })

  watch(deps, render, { deep: true })

  return { chart, render }
}
