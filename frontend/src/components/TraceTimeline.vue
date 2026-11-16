<script setup lang="ts">
/** 执行轨迹时间线：展示 agent 每一步的耗时与结论，体现可追溯性。 */
import type { TraceStep, Usage } from '../api/types'

defineProps<{
  trace: TraceStep[]
  usage: Usage
  elapsedMs: number
}>()

const statusIcon: Record<TraceStep['status'], string> = {
  ok: '✓',
  warn: '!',
  error: '✕',
  skipped: '–',
}
</script>

<template>
  <section class="panel">
    <h2>
      Agent 执行轨迹
      <span>{{ (elapsedMs / 1000).toFixed(1) }} s · 模型调用 {{ usage.calls }} 次 · {{ usage.prompt_tokens }}+{{ usage.completion_tokens }} tokens</span>
    </h2>
    <ol class="trace">
      <li v-for="(step, index) in trace" :key="index" :class="'trace-' + step.status">
        <span class="trace-icon">{{ statusIcon[step.status] }}</span>
        <span class="trace-name">{{ step.step }}</span>
        <span class="trace-detail">{{ step.detail }}</span>
        <span class="trace-time">{{ step.duration_ms }} ms</span>
      </li>
    </ol>
  </section>
</template>
