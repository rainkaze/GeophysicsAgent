<script setup lang="ts">
/** 方案详情：主方法理由、采集参数、外业布置、风险与验证。 */
import { computed } from 'vue'

import type { FieldDesign, MethodAssessment, SurveyPlan } from '../api/types'

const props = defineProps<{
  plan: SurveyPlan
  assessments: MethodAssessment[]
  design: FieldDesign | null
  warnings: string[]
}>()

const primaryItem = computed(() => props.plan.items.find((item) => item.role === '主方法') ?? null)

const primaryAssessment = computed<MethodAssessment | null>(() => {
  const item = primaryItem.value
  if (!item) return null
  return props.assessments.find((a) => a.method === item.method) ?? null
})

const supports = computed(() =>
  props.plan.items.filter((item) => item.role === '辅助方法' || item.role === '验证方法'),
)
const excluded = computed(() => props.plan.items.filter((item) => item.role === '不建议采用'))

/** 排除方法的原因前缀：深度不足 / 物性不匹配 / 其他 */
function exclusionLabel(method: string): string {
  const assessment = props.assessments.find((a) => a.method === method)
  if (!assessment) return '未采用'
  if (!assessment.feasible) return '深度不足'
  if (assessment.suitability === '不适用') return '物性不匹配'
  return assessment.suitability
}
</script>

<template>
  <section class="panel">
    <h2>方案要点</h2>
    <p class="summary">{{ plan.summary }}</p>

    <template v-if="primaryItem && primaryAssessment">
      <h3>主方法：{{ primaryAssessment.method_cn }}</h3>
      <dl class="kv">
        <dt>选择理由</dt>
        <dd>{{ primaryItem.rationale }}</dd>
        <dt>深度校核</dt>
        <dd>最大探测深度 {{ primaryAssessment.max_depth_m }} m，{{ primaryAssessment.depth_check }}</dd>
        <dt>理论分辨率</dt>
        <dd>{{ primaryAssessment.resolution_basis }}</dd>
        <dt>物理依据</dt>
        <dd>{{ primaryAssessment.physics_basis }}</dd>
        <dt>限制应对</dt>
        <dd>{{ primaryItem.mitigation ?? '本次未提出额外应对措施' }}</dd>
      </dl>

      <h3>采集参数</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr><th>参数</th><th>取值</th></tr>
          </thead>
          <tbody>
            <tr v-for="(value, key) in primaryAssessment.acquisition.items" :key="key">
              <td>{{ key }}</td>
              <td>{{ value }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>

    <p v-else class="muted">当前条件下没有可承担主方法的方案，建议先做方法试验或分段设计。</p>

    <template v-if="supports.length">
      <h3>辅助与验证</h3>
      <ul class="bullet">
        <li v-for="item in supports" :key="item.method">
          <b>{{ assessments.find((a) => a.method === item.method)?.method_cn ?? item.method }}</b>：{{ item.rationale }}
          <span v-if="item.mitigation" class="muted">（{{ item.mitigation }}）</span>
        </li>
      </ul>
    </template>

    <template v-if="excluded.length">
      <h3>不建议采用</h3>
      <ul class="bullet">
        <li v-for="item in excluded" :key="item.method">
          <b>{{ assessments.find((a) => a.method === item.method)?.method_cn ?? item.method }}</b>
          <span class="tag tag-bad">{{ exclusionLabel(item.method) }}</span>：{{ item.rationale }}
        </li>
      </ul>
    </template>
  </section>

  <section v-if="design && design.primary_method" class="panel">
    <h2>外业布置与工作量</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr><th>项目</th><th>估算值</th></tr>
        </thead>
        <tbody>
          <tr><td>主测线长度</td><td>{{ design.main_line_length_m }} m</td></tr>
          <tr><td>测线数量</td><td>{{ design.line_count }} 条（含两侧平行测线）</td></tr>
          <tr><td>横测线间距</td><td>{{ design.cross_line_spacing_m === null ? '不需要' : design.cross_line_spacing_m + ' m' }}</td></tr>
          <tr><td>总测线长度</td><td>{{ design.total_line_km }} km</td></tr>
          <tr><td>测点总数</td><td>{{ design.station_count === null ? '按现场标定' : design.station_count + ' 点' }}</td></tr>
          <tr><td>相对成本</td><td>{{ design.relative_cost_index }}（{{ design.cost_band }}成本档）</td></tr>
        </tbody>
      </table>
    </div>
    <details class="basis">
      <summary>估算依据（{{ design.basis.length }} 条）</summary>
      <ul class="bullet">
        <li v-for="(line, index) in design.basis" :key="index">{{ line }}</li>
      </ul>
    </details>
  </section>

  <section class="panel">
    <h2>风险与对策</h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr><th>风险</th><th>影响</th><th>对策</th></tr>
        </thead>
        <tbody>
          <tr v-for="(risk, index) in plan.risks" :key="index">
            <td>{{ risk.risk }}</td>
            <td>{{ risk.impact }}</td>
            <td>{{ risk.response }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <h3>验证措施</h3>
    <ul class="bullet">
      <li v-for="(item, index) in plan.verification" :key="index">{{ item }}</li>
    </ul>

    <template v-if="plan.missing_information.length">
      <h3>待补资料</h3>
      <ul class="bullet">
        <li v-for="(item, index) in plan.missing_information" :key="index">{{ item }}</li>
      </ul>
    </template>

    <template v-if="warnings.length">
      <h3>系统提示</h3>
      <ul class="bullet warn-list">
        <li v-for="(item, index) in warnings" :key="index">{{ item }}</li>
      </ul>
    </template>
  </section>
</template>
