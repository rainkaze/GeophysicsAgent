/**
 * 与后端 `domain/schemas.py` 一一对应的类型定义。
 * 修改后端响应结构时，这里必须同步更新。
 */

export type Mode = 'agent' | 'clarification' | 'degraded'
export type TraceStatus = 'ok' | 'warn' | 'error' | 'skipped'
export type EvidenceQuality = 'strong' | 'weak' | 'empty'

export interface DepthRange {
  min_m: number
  max_m: number
}

export interface SiteConditions {
  target: string | null
  medium: string | null
  depth: DepthRange | null
  surface: string | null
  interference: string[]
  budget: string | null
  site_length_m: number | null
  accuracy: string | null
  free_text: string | null
}

export interface ConditionView {
  target: string | null
  medium: string | null
  depth: string | null
  surface: string | null
  interference: string | null
  budget: string | null
  site_length: string | null
}

export interface AcquisitionParams {
  items: Record<string, string>
}

export interface MethodAssessment {
  method: string
  method_cn: string
  max_depth_m: number
  depth_margin: number
  depth_check: string
  feasible: boolean
  suitability: string
  suitability_reason: string
  vertical_resolution_m: number | null
  resolution_basis: string
  station_spacing_m: number | null
  array_length_m: number | null
  relative_cost: string
  cost_index: number
  acquisition: AcquisitionParams
  physics_basis: string
  deployment_requirement: string
  limitations: string[]
  interference_notes: string[]
}

export interface FieldDesign {
  primary_method: string | null
  main_line_length_m: number
  line_count: number
  cross_line_spacing_m: number | null
  total_line_km: number
  station_count: number | null
  relative_cost_index: number
  cost_band: string
  basis: string[]
}

export interface PlanItem {
  method: string
  role: string
  rationale: string
  mitigation: string | null
}

export interface Risk {
  risk: string
  impact: string
  response: string
}

export interface Violation {
  code: string
  severity: 'error' | 'warning'
  message: string
}

export interface SurveyPlan {
  summary: string
  items: PlanItem[]
  risks: Risk[]
  verification: string[]
  missing_information: string[]
  violations: Violation[]
  degraded: boolean
  narrative: string
}

export interface Evidence {
  id: string
  title: string
  content: string
  source: string
  page: number | null
  verification_status: string
  score: number
  matched_terms: string[]
  source_url: string | null
  citation: string | null
}

export interface TraceStep {
  step: string
  status: TraceStatus
  detail: string
  duration_ms: number
}

export interface Usage {
  calls: number
  prompt_tokens: number
  completion_tokens: number
}

export interface RecommendResponse {
  mode: Mode
  conversation_id: string
  answer: string
  needs_clarification: boolean
  questions: string[]
  conditions: SiteConditions
  conditions_view: ConditionView
  missing_information: string[]
  plan: SurveyPlan | null
  assessments: MethodAssessment[]
  design: FieldDesign | null
  evidence: Evidence[]
  evidence_quality: EvidenceQuality
  warnings: string[]
  trace: TraceStep[]
  usage: Usage
  elapsed_ms: number
  disclaimer: string
}

export interface Scenario {
  sid: string
  title: string
  query: string
  target_cn: string
  medium_cn: string
  depth_range: string
}
