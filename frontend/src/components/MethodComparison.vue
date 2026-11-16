<script setup lang="ts">
/** 方法比选表：六种方法的判定、余量、分辨率、成本与方案角色。 */
import { computed } from 'vue'

import type { MethodAssessment, PlanItem } from '../api/types'

const props = defineProps<{
  assessments: MethodAssessment[]
  items: PlanItem[]
}>()

const roleOf = computed<Record<string, string>>(() => {
  const map: Record<string, string> = {}
  for (const item of props.items) {
    map[item.method] = item.role
  }
  return map
})

function suitabilityClass(suitability: string): string {
  switch (suitability) {
    case '首选':
      return 'tag tag-primary'
    case '适用':
      return 'tag tag-ok'
    case '辅助':
      return 'tag tag-muted'
    case '受限':
      return 'tag tag-warn'
    default:
      return 'tag tag-bad'
  }
}
</script>

<template>
  <section class="panel">
    <h2>方法比选 <span>{{ assessments.length }} 种方法</span></h2>
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>方法</th>
            <th>判定</th>
            <th>深度校核</th>
            <th>垂向分辨率</th>
            <th>成本</th>
            <th>方案角色</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in assessments" :key="a.method" :class="{ 'row-primary': roleOf[a.method] === '主方法' }">
            <td>{{ a.method_cn }}</td>
            <td><span :class="suitabilityClass(a.suitability)">{{ a.suitability }}</span></td>
            <td>{{ a.depth_check }}</td>
            <td>{{ a.vertical_resolution_m === null ? '无垂向分辨' : a.vertical_resolution_m + ' m' }}</td>
            <td>{{ a.relative_cost }}</td>
            <td>{{ roleOf[a.method] ?? '未采用' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
