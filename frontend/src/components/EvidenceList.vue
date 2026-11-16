<script setup lang="ts">
/** 课程知识证据列表：显示相关性等级、命中词与核对状态。 */
import type { Evidence, EvidenceQuality } from '../api/types'

defineProps<{
  evidence: Evidence[]
  quality: EvidenceQuality
}>()

const qualityText: Record<EvidenceQuality, string> = {
  strong: '相关性良好，可作为课程依据',
  weak: '相关性偏弱，引用前请人工核对',
  empty: '未检索到相关条目，以下结论不含课程出处',
}

const qualityClass: Record<EvidenceQuality, string> = {
  strong: 'banner banner-ok',
  weak: 'banner banner-warn',
  empty: 'banner banner-bad',
}
</script>

<template>
  <section class="panel">
    <h2>课程知识依据 <span>{{ evidence.length }} 条</span></h2>
    <p :class="qualityClass[quality]">{{ qualityText[quality] }}</p>

    <article v-for="item in evidence" :key="item.id" class="evidence">
      <header>
        <b>{{ item.title }}</b>
        <span class="tag tag-muted">相关度 {{ item.score }}</span>
      </header>
      <p>{{ item.content }}</p>
      <p class="meta">
        {{ item.source }} · {{ item.page === null ? '页码未标注' : '第 ' + item.page + ' 页' }} ·
        {{ item.verification_status }}
      </p>
      <p v-if="item.matched_terms.length" class="meta">命中词：{{ item.matched_terms.join('、') }}</p>
      <p v-if="item.citation" class="meta">{{ item.citation }}</p>
      <a v-if="item.source_url" :href="item.source_url" target="_blank" rel="noopener noreferrer">
        打开资料来源 ↗
      </a>
    </article>
  </section>
</template>
