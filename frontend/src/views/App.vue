<script setup lang="ts">
import { computed, ref } from 'vue'
import DOMPurify from 'dompurify'
import { marked } from 'marked'
import { recommend } from '../api/client'

const input = ref('')
const loading = ref(false)
const error = ref('')
const result = ref<any>(null)
const renderedAnswer = computed(() =>
  DOMPurify.sanitize(marked.parse(result.value?.answer ?? '') as string),
)
const example = '滨海软土场地，地下水位约1米，需要调查0到20米横波速度结构，附近有轻微交通振动。请给出物探勘察建议。'

async function submit() {
  if (input.value.trim().length < 8 || loading.value) return
  loading.value = true
  error.value = ''
  result.value = null
  try { result.value = await recommend(input.value.trim()) }
  catch (e) { error.value = e instanceof Error ? e.message : '请求失败' }
  finally { loading.value = false }
}
</script>

<template>
  <main class="shell">
    <header><div class="brand">GEOPHYSICS · AGENT</div><h1>工程物探勘察方案推荐</h1>
      <p>以课程知识和参数工具为依据的工程物探辅助决策原型</p></header>
    <section class="panel input-panel">
      <label for="scenario">描述你的勘察场景</label>
      <textarea id="scenario" v-model="input" rows="5" placeholder="例如：场地介质、目标、埋深、干扰条件和调查目的……" />
      <div class="actions"><button class="subtle" @click="input = example">填入示例场景</button>
        <button :disabled="loading || input.trim().length < 8" @click="submit">{{ loading ? 'Agent 正在分析…' : '生成方案' }}</button></div>
    </section>
    <p v-if="error" class="error">{{ error }}</p>
    <template v-if="result">
      <div class="status">● 真实 LLM 模式 · 对话 {{ result.conversation_id }}</div>
      <section class="panel"><h2>推荐方案</h2><div class="answer markdown" v-html="renderedAnswer"></div></section>
      <section class="panel"><h2>场景条件识别</h2>
        <div v-if="Object.keys(result.extracted_conditions).length" class="condition-list">
          <span v-for="(value, key) in result.extracted_conditions" :key="key"><b>{{ key }}</b>：{{ value }}</span>
        </div>
        <p v-else class="muted">Agent 尚未从本轮完成结构化条件确认。</p>
        <p v-if="result.missing_information?.length" class="warning">建议补充：{{ result.missing_information.join('、') }}</p>
      </section>
      <section class="grid">
        <article class="panel"><h2>课程知识依据 <span>{{ result.evidence.length }} 条</span></h2>
          <p v-if="!result.evidence.length" class="muted">当前知识库未检索到匹配条目，请谨慎看待模型常识性回答。</p>
          <div v-for="item in result.evidence" :key="item.id" class="evidence"><b>{{ item.title }}</b><p>{{ item.content }}</p>
            <small>{{ item.source }} · {{ item.page ? '第 '+item.page+' 页' : '页码不适用/待补' }} · {{ item.verification_status }}</small>
            <small v-if="item.citation">{{ item.citation }}</small>
            <a v-if="item.source_url" :href="item.source_url" target="_blank" rel="noopener noreferrer">打开资料来源 ↗</a></div>
        </article>
        <article class="panel"><h2>方法参数比较</h2>
          <p v-if="!result.tool_result" class="muted">信息不足，Agent 尚未调用参数工具。</p>
          <template v-else><p>{{ result.tool_result.target_contrast }}</p>
            <div v-for="(method, key) in result.tool_result.methods" :key="key" class="method">
              <b>{{ method.method_cn }}</b><span>{{ method.suitability }} · 深度 {{ method.max_depth_m }} m</span>
              <small>{{ method.suitability_reason }}</small></div></template>
        </article>
      </section>
      <section class="panel"><h2>Agent 执行过程</h2><p v-for="event in result.events" :key="event.event">✓ {{ event.detail }}（{{ event.status }}）</p></section>
      <p class="disclaimer">{{ result.disclaimer }}</p>
    </template>
    <footer>课程研究原型 · 方案须经现场试验和专业人员复核</footer>
  </main>
</template>
