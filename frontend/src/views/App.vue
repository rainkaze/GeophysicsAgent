<script setup lang="ts">
/** 主页面：输入场景 → 调用 agent → 结构化展示方案与执行轨迹。 */
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { computed, onMounted, ref } from 'vue'

import { fetchScenarios, recommend } from '../api/client'
import type { RecommendResponse, Scenario } from '../api/types'
import EvidenceList from '../components/EvidenceList.vue'
import MethodComparison from '../components/MethodComparison.vue'
import PlanDetail from '../components/PlanDetail.vue'
import TraceTimeline from '../components/TraceTimeline.vue'

const input = ref('')
const loading = ref(false)
const error = ref('')
const result = ref<RecommendResponse | null>(null)
const conversationId = ref<string | null>(null)
const scenarios = ref<Scenario[]>([])

const canSubmit = computed(() => input.value.trim().length >= 8 && !loading.value)

const renderedNarrative = computed(() => {
  if (!result.value) return ''
  return DOMPurify.sanitize(marked.parse(result.value.answer) as string)
})

const modeText = computed(() => {
  if (!result.value) return ''
  if (result.value.mode === 'clarification') return '需要补充信息'
  if (result.value.mode === 'degraded') return '规则模式（模型未参与或未通过校验）'
  return 'Agent 模式（模型决策 + 规则校验通过）'
})

const modeClass = computed(() => {
  if (!result.value) return ''
  if (result.value.mode === 'clarification') return 'badge badge-warn'
  if (result.value.mode === 'degraded') return 'badge badge-muted'
  return 'badge badge-ok'
})

const conditionRows = computed(() => {
  const view = result.value?.conditions_view
  if (!view) return []
  return [
    { label: '探测目标', value: view.target },
    { label: '主要介质', value: view.medium },
    { label: '目标埋深', value: view.depth },
    { label: '地表条件', value: view.surface },
    { label: '场地干扰', value: view.interference },
    { label: '预算约束', value: view.budget },
    { label: '场地长度', value: view.site_length },
  ].filter((row) => row.value !== null && row.value !== '')
})

onMounted(async () => {
  try {
    scenarios.value = await fetchScenarios()
  } catch {
    scenarios.value = []
  }
})

async function submit(): Promise<void> {
  if (!canSubmit.value) return
  loading.value = true
  error.value = ''
  try {
    const response = await recommend(input.value.trim(), conversationId.value)
    result.value = response
    conversationId.value = response.conversation_id
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : '请求失败'
  } finally {
    loading.value = false
  }
}

function useScenario(scenario: Scenario): void {
  input.value = scenario.query
}

function newConversation(): void {
  conversationId.value = null
  result.value = null
  error.value = ''
  input.value = ''
}
</script>

<template>
  <main class="shell">
    <header class="hero">
      <div class="brand">GEOPHYSICS · AGENT</div>
      <h1>工程物探勘察方案推荐</h1>
      <p class="muted">
        自然语言场景 → 六种方法确定性评估 → 模型决策 → 规则校验 → 结构化方案
      </p>
    </header>

    <section class="panel input-panel">
      <label for="scenario">描述你的勘察场景</label>
      <textarea
        id="scenario"
        v-model="input"
        rows="5"
        placeholder="例如：山区路基，围岩为灰岩，需要探测溶洞，埋深 4~15 m，地表碎石覆盖、地形起伏较大……"
      />
      <div class="actions">
        <button class="subtle" :disabled="loading" @click="newConversation">新对话</button>
        <button :disabled="!canSubmit" @click="submit">
          {{ loading ? 'Agent 正在分析…' : '生成方案' }}
        </button>
      </div>
      <div v-if="scenarios.length" class="chips">
        <span class="chips-label">示例场景：</span>
        <button
          v-for="scenario in scenarios"
          :key="scenario.sid"
          class="chip"
          :disabled="loading"
          @click="useScenario(scenario)"
        >
          {{ scenario.title }}
        </button>
      </div>
      <p v-if="conversationId" class="muted small">
        当前会话 {{ conversationId.slice(0, 8) }}，可直接追问（例如"埋深改成 60 m 呢？"）
      </p>
    </section>

    <p v-if="error" class="error">{{ error }}</p>

    <template v-if="result">
      <div class="status">
        <span :class="modeClass">{{ modeText }}</span>
        <span class="muted small">耗时 {{ (result.elapsed_ms / 1000).toFixed(1) }} s</span>
      </div>

      <section v-if="conditionRows.length" class="panel">
        <h2>场景条件识别</h2>
        <div class="condition-grid">
          <div v-for="row in conditionRows" :key="row.label" class="condition">
            <span class="condition-label">{{ row.label }}</span>
            <span class="condition-value">{{ row.value }}</span>
          </div>
        </div>
        <p v-if="result.needs_clarification" class="muted">
          还缺关键字段，补齐后才能给出可靠方案。
        </p>
      </section>

      <section v-if="result.needs_clarification" class="panel">
        <h2>需要补充</h2>
        <ol class="bullet">
          <li v-for="(question, index) in result.questions" :key="index">{{ question }}</li>
        </ol>
      </section>

      <template v-if="result.plan">
        <PlanDetail
          :plan="result.plan"
          :assessments="result.assessments"
          :design="result.design"
          :warnings="result.warnings"
        />
        <MethodComparison :assessments="result.assessments" :items="result.plan.items" />
        <EvidenceList :evidence="result.evidence" :quality="result.evidence_quality" />
        <TraceTimeline :trace="result.trace" :usage="result.usage" :elapsed-ms="result.elapsed_ms" />

        <details class="panel">
          <summary>查看完整文字版（Markdown）</summary>
          <div class="markdown" v-html="renderedNarrative"></div>
        </details>
      </template>

      <p v-else-if="result.mode === 'clarification'" class="panel muted">
        {{ result.answer }}
      </p>

      <p class="disclaimer">{{ result.disclaimer }}</p>
    </template>

    <footer>课程研究原型 · 方案须经现场试验与专业人员复核</footer>
  </main>
</template>
