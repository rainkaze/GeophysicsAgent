import json
import re
PRIMARY, SUPPORT, VERIFICATION, EXCLUDED = ('主方法', '辅助方法', '验证方法', '不建议采用')
ROLE_ALIASES = {'主方法': PRIMARY, 'primary': PRIMARY, '主要方法': PRIMARY, '辅助': SUPPORT, '辅助方法': SUPPORT, 'support': SUPPORT, '验证': VERIFICATION, '验证方法': VERIFICATION, 'verification': VERIFICATION, '不建议': EXCLUDED, '不建议采用': EXCLUDED, 'excluded': EXCLUDED}
METHOD_CN = {'gpr': '探地雷达（GPR）', 'dc': '直流电阻率（DC/ERT）', 'surface_wave': '面波地震（MASW）', 'refraction': '地震折射（Refraction）', 'magnetic': '磁法勘探', 'fdem': '频域电磁（FDEM）', 'tem': '瞬变电磁（TEM）', 'das': '分布式光纤声学（DAS）'}
METHOD_ORDER = ('gpr', 'dc', 'surface_wave', 'refraction', 'magnetic', 'fdem', 'tem', 'das')
ROLE_LABEL = {PRIMARY: '**主方法**', SUPPORT: '辅助方法', VERIFICATION: '验证方法', EXCLUDED: '不建议采用'}
_UXO_PRIMARY = ('magnetic', 'fdem')
_VERIFICATION_KEYWORDS = ('钻孔', '钻探', 'CPT', '静力触探', '试验剖面', '原位测试', '开挖验证')
_FIBER_KEYWORDS = ('光缆', '钻孔', '光纤')
DISCLAIMER = '本方案为课程演示级辅助建议：最大探测深度与分辨率为教学用经验估算，必须经现场试验剖面标定；物探解释具有多解性，需结合钻孔、原位测试与工程师判断。'

def _strip_fence(text):
    raw = (text or '').strip()
    if raw.startswith('```'):
        raw = re.sub('^```[a-zA-Z]*\\s*', '', raw)
        raw = re.sub('\\s*```$', '', raw)
    if not raw.startswith('{'):
        start = raw.find('{')
        end = raw.rfind('}')
        if start >= 0 and end > start:
            raw = raw[start:end + 1]
    return raw

def parse_draft(llm_json):
    raw = _strip_fence(llm_json)
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    items = []
    seen = set()
    for item in data.get('items') or []:
        if not isinstance(item, dict):
            continue
        method = str(item.get('method', '')).strip().lower()
        if method not in METHOD_ORDER or method in seen:
            continue
        role = ROLE_ALIASES.get(str(item.get('role', '')).strip())
        if role is None:
            continue
        seen.add(method)
        items.append({'method': method, 'role': role, 'rationale': str(item.get('rationale') or '').strip(), 'mitigation': str(item.get('mitigation')).strip() if item.get('mitigation') else None})
    if not items:
        return None
    risks = []
    for risk in data.get('risks') or []:
        if isinstance(risk, dict):
            risks.append({'risk': str(risk.get('risk') or '').strip(), 'impact': str(risk.get('impact') or '').strip(), 'response': str(risk.get('response') or '').strip()})
    verification = [str(v).strip() for v in data.get('verification') or [] if str(v).strip()]
    missing = [str(v).strip() for v in data.get('missing_information') or [] if str(v).strip()]
    return {'summary': str(data.get('summary') or '').strip(), 'items': items, 'risks': risks, 'verification': verification, 'missing_information': missing}

def _primary_item(draft):
    for item in draft['items']:
        if item['role'] == PRIMARY:
            return item
    return None

def _violation(code, severity, message):
    return {'code': code, 'severity': severity, 'message': message}

def verify(draft, conditions, bundle):
    violations = []
    primary_item = _primary_item(draft)
    methods = bundle['methods']
    recommended = bundle['recommended_primary']
    if primary_item is None:
        if recommended:
            violations.append(_violation('V001', 'error', '方案没有指定主方法（评估器推荐：' + '、'.join((METHOD_CN[m] for m in recommended)) + '）'))
        else:
            violations.append(_violation('V001', 'warning', '八种演示方法在当前条件下没有合适主方法，方案如实不指定主方法'))
        return violations
    primary = primary_item['method']
    assessment = methods[primary]
    if not assessment['feasible']:
        violations.append(_violation('V002', 'error', f"{assessment['method_cn']} 的最大探测深度 {assessment['max_depth_m']:g} m 不足目标埋深 {bundle['design_depth_m']:g} m，不能作为主方法"))
    if assessment['suitability'] == '不适用':
        violations.append(_violation('V003', 'error', f"{assessment['method_cn']} 对{bundle['target_cn']}判为不适用：{assessment['suitability_reason']}"))
    if assessment['depth_margin'] < 1.15:
        adequate = [item for item in methods.values() if item['feasible'] and item['depth_margin'] >= 1.15 and (item['suitability'] in ('首选', '适用', '受限'))]
        if adequate:
            violations.append(_violation('V004', 'error', f"{assessment['method_cn']} 深度余量仅 {assessment['depth_margin']:.2f}×，不足 1.15×，不能承担主方法（可改用余量更大的方法）"))
        else:
            violations.append(_violation('V004', 'warning', f"当前埋深下没有方法满足 1.15× 余量，{assessment['method_cn']}（{assessment['depth_margin']:.2f}×）已是次优选择，建议分段设计或钻孔为主"))
    if assessment['suitability'] == '受限' and (not primary_item['mitigation']):
        violations.append(_violation('V005', 'error', f"{assessment['method_cn']} 被判为受限（{assessment['suitability_reason']}），作为主方法必须给出 mitigation"))
    if primary not in recommended and assessment['suitability'] != '受限':
        violations.append(_violation('V006', 'warning', f"主方法 {assessment['method_cn']} 与评估器推荐（{'、'.join((METHOD_CN[m] for m in recommended)) or '无'}）不一致，需在 rationale 中说明理由"))
    for item in draft['items']:
        item_assessment = methods[item['method']]
        if item['role'] == EXCLUDED and item_assessment['suitability'] == '首选':
            violations.append(_violation('V007', 'error', f"{METHOD_CN[item['method']]} 被判为首选方法，不能排除"))
        if item['role'] == PRIMARY and item['method'] != primary:
            violations.append(_violation('V008', 'error', f"出现多个主方法（{METHOD_CN[item['method']]}）"))
    if assessment['interference_notes'] and (not primary_item['mitigation']):
        violations.append(_violation('V009', 'error', f"场地干扰（{'；'.join(assessment['interference_notes'][:2])}）会影响 {assessment['method_cn']}，主方法必须给出 mitigation"))
    if conditions.get('target') == 'uxo' and primary not in _UXO_PRIMARY:
        violations.append(_violation('V010', 'warning', 'UXO 探测的主方法应为磁法或 FDEM，当前主方法不符合常规做法'))
    if primary == 'das':
        mitigation = primary_item['mitigation'] or ''
        if not any((word in mitigation for word in _FIBER_KEYWORDS)):
            violations.append(_violation('V011', 'error', 'DAS 必须依赖钻孔内光缆或既有通信光缆，主方法的 mitigation 未说明光缆来源'))
    verification_text = '；'.join(draft['verification'])
    if not any((word in verification_text for word in _VERIFICATION_KEYWORDS)):
        violations.append(_violation('V012', 'error', '验证措施缺少钻孔/原位测试/试验剖面等可执行动作'))
    if len(draft['risks']) < 3:
        violations.append(_violation('V013', 'warning', f"风险只列了 {len(draft['risks'])} 条，建议至少 3 条（深度、干扰、多解性）"))
    if conditions.get('budget') == 'low' and bundle['design']['cost_band'] == '高':
        violations.append(_violation('V014', 'error', f"用户预算偏低，但该方案估算为高成本档（相对成本指数 {bundle['design']['relative_cost_index']:.1f}）"))
    return violations

def has_errors(violations):
    return any((item['severity'] == 'error' for item in violations))

def fallback_plan(bundle):
    methods = bundle['methods']
    items = []
    primary_method = bundle['recommended_primary'][0] if bundle['recommended_primary'] else None
    if primary_method is not None:
        primary = methods[primary_method]
        mitigation = None
        if primary['suitability'] == '受限':
            mitigation = '受限条件需用试验剖面标定，并只在其有效深度段内使用'
        elif primary['interference_notes']:
            mitigation = '避开干扰源作业窗口，并做重复观测以识别假异常'
        if primary_method == 'das':
            mitigation = '需钻孔内光缆或既有通信光缆，否则该方法无法开展'
        resolution = f"{primary['vertical_resolution_m']:g} m" if primary['vertical_resolution_m'] is not None else '无垂向分辨能力'
        items.append({'method': primary_method, 'role': PRIMARY, 'rationale': f"{primary['method_cn']} 深度余量 {primary['depth_margin']:.2f}×、垂向分辨率约 {resolution}，对{bundle['target_cn']}的物性响应为：{bundle['target_contrast']}", 'mitigation': mitigation})
        support_candidates = [method for method in bundle['recommended_primary'][1:] + bundle['recommended_support'] if method != primary_method]
        for method in support_candidates:
            if len([item for item in items if item['role'] == SUPPORT]) >= 2:
                break
            assessment = methods[method]
            items.append({'method': method, 'role': SUPPORT, 'rationale': f"{assessment['method_cn']} 可提供交叉验证：{assessment['suitability_reason']}", 'mitigation': None})
    assigned = {item['method'] for item in items}
    for method in METHOD_ORDER:
        if method in assigned:
            continue
        assessment = methods[method]
        if not assessment['feasible']:
            reason = f"深度不可行：最大探测深度 {assessment['max_depth_m']:g} m 小于目标埋深 {bundle['design_depth_m']:g} m"
        elif assessment['suitability'] == '不适用':
            reason = f"物性不匹配：{assessment['suitability_reason']}"
        elif assessment['suitability'] == '受限':
            reason = f"受限，不宜作为主方法：{assessment['suitability_reason']}"
        else:
            reason = f"本次不作为主要手段：{assessment['suitability_reason']}"
        items.append({'method': method, 'role': EXCLUDED, 'rationale': reason, 'mitigation': None})
        assigned.add(method)
    risks = []
    if primary_method is not None:
        for limitation in methods[primary_method]['limitations'][:3]:
            risks.append({'risk': limitation[:80], 'impact': '可能导致异常漏判或误判', 'response': '用辅助方法交叉验证，并在异常段布置钻孔'})
    risks.append({'risk': '物探解释的多解性', 'impact': '异常体性质可能与推断不符', 'response': '以钻孔与原位测试标定，不把物探结果直接当作设计依据'})
    if primary_method is not None:
        summary = f"针对{bundle['target_cn']}（{bundle['medium_cn']}，{bundle['depth_range']}），建议以{methods[primary_method]['method_cn']}为主，配合辅助方法交叉验证，并以钻探验证异常。"
    else:
        summary = f"针对{bundle['target_cn']}（{bundle['medium_cn']}，{bundle['depth_range']}），八种演示方法在当前条件下均受限或不适用，没有可直接推荐的主方法，建议扩展方法范围（反射/微动/重力/测井等）或钻探为主、分段设计。"
    return {'summary': summary, 'items': items, 'risks': risks[:5], 'verification': ['每个异常段布置至少 1 个钻孔，核对异常体性质与埋深', '开工前在已知段做试验剖面，标定采集参数与信噪比'], 'missing_information': ['场地可布设长度与施工作业窗口']}

def _cell(value):
    return str(value).replace('|', '／').replace('\n', ' ').strip()

def _conditions_table(bundle, conditions):
    view = bundle.get('conditions_view') or {}
    rows = [('探测目标', view.get('target') or '未识别'), ('主要介质', view.get('medium') or '未识别'), ('目标埋深', bundle.get('depth_range') or '未识别'), ('地表条件', view.get('surface') or '未说明'), ('场地干扰', view.get('interference') or '未说明'), ('预算约束', view.get('budget') or '未说明'), ('场地长度', view.get('site_length') or '未说明')]
    body = '\n'.join((f'| {_cell(name)} | {_cell(value)} |' for name, value in rows))
    return '| 项目 | 内容 |\n|---|---|\n' + body

def _comparison_table(plan, bundle):
    roles = {item['method']: item['role'] for item in plan['items']}
    lines = ['| 方法 | 判定 | 深度余量 | 垂向分辨率 | 相对成本 | 方案角色 |', '|---|---|---|---|---|---|']
    for method in METHOD_ORDER:
        item = bundle['methods'][method]
        resolution = f"{item['vertical_resolution_m']:g} m" if item['vertical_resolution_m'] is not None else '无垂向分辨'
        role = ROLE_LABEL.get(roles.get(method), '未采用') if method in roles else '未采用'
        lines.append(f"| {_cell(item['method_cn'])} | {item['suitability']} | {item['depth_check']} | {resolution} | {item['relative_cost']} | {role} |")
    return '\n'.join(lines)

def _primary_section(plan, bundle):
    primary = next((item for item in plan['items'] if item['role'] == PRIMARY), None)
    if primary is None:
        return ['### 主方法', '', '八种演示方法在当前条件下均受限或不适用，没有可直接推荐的主方法。', '建议扩展方法范围（反射/微动/重力/测井等），或钻探为主、分段设计。', '']
    assessment = bundle['methods'][primary['method']]
    lines = [f"### 主方法：{assessment['method_cn']}", '', f"- **选择理由**：{primary['rationale']}", f"- **深度校核**：最大探测深度 {assessment['max_depth_m']:g} m，目标埋深 {bundle['design_depth_m']:g} m，{assessment['depth_check']}", f"- **理论分辨率**：{assessment['resolution_basis']}", f"- **物理依据**：{assessment['physics_basis']}", f"- **布设要求**：{assessment['deployment_requirement']}"]
    if primary['mitigation']:
        lines.append(f"- **限制应对**：{primary['mitigation']}")
    else:
        lines.append('- **限制应对**：本次未提出额外应对措施')
    return lines

def _acquisition_table(bundle, design):
    method = design['primary_method']
    if method is None:
        return '尚未确定主方法，暂不给出采集参数。'
    lines = ['| 参数 | 取值 |', '|---|---|']
    for key, value in bundle['methods'][method]['acquisition'].items():
        lines.append(f'| {_cell(key)} | {_cell(value)} |')
    return '\n'.join(lines)

def _design_table(design):
    if design['primary_method'] is None:
        return '尚未确定主方法，暂不给工作量估算。'
    rows = [('主测线长度', f"{design['main_line_length_m']:g} m"), ('测线数量', f"{design['line_count']} 条（含两侧平行测线）"), ('横测线间距', f"{design['cross_line_spacing_m']:g} m" if design['cross_line_spacing_m'] else '不需要'), ('总测线长度', f"{design['total_line_km']:g} km"), ('测点总数', f"{design['station_count']} 点" if design['station_count'] else '按现场标定'), ('相对成本指数', f"{design['relative_cost_index']:.1f}（{design['cost_band']}成本档，GPR 每 100 m = 1）")]
    body = '\n'.join((f'| {_cell(name)} | {_cell(value)} |' for name, value in rows))
    return '| 项目 | 估算值 |\n|---|---|\n' + body

def _evidence_section(evidence):
    if not evidence:
        return ['本次未检索到匹配的课程知识条目，以下结论不含课程出处，请谨慎使用。']
    lines = [f'本次检索到 {len(evidence)} 条课程知识（混合检索 + Rerank 重排）：', '']
    for index, item in enumerate(evidence, start=1):
        content = item.get('content', '')
        headline, _, body = content.partition('\n')
        if '｜' not in headline or len(headline) >= 200:
            headline, body = ('', content)
        body = ' '.join(body.split())
        score = item.get('score')
        score_text = f'（相关度 {score:.2f}）' if isinstance(score, (int, float)) else ''
        lines.append(f'{index}. **{_cell(headline)}**{score_text}' if headline else f'{index}.{score_text}')
        lines.append(f"   {_cell(body[:240])}{('…' if len(body) > 240 else '')}")
    return lines

def render(plan, bundle, conditions, design, evidence, warnings, degraded):
    parts = []
    target_cn = bundle.get('target_cn') or '未识别目标'
    parts.append(f'# {target_cn}｜工程物探勘察方案')
    if degraded:
        parts.extend(['', '> ⚠️ **本方案由规则引擎生成**（模型输出未通过校验或未配置模型），数值仍来自课程参数表与物理关系计算，但未经过模型的语言组织。'])
    parts.extend(['', f"> {plan['summary']}"])
    parts.extend(['', '## 一、条件复核', '', _conditions_table(bundle, conditions)])
    parts.extend(['', '## 二、方法比选', '', _comparison_table(plan, bundle)])
    parts.extend(['', '## 三、方案要点', ''])
    parts.extend(_primary_section(plan, bundle))
    supports = [item for item in plan['items'] if item['role'] in (SUPPORT, VERIFICATION)]
    if supports:
        parts.extend(['', '### 辅助与验证方法', ''])
        for item in supports:
            assessment = bundle['methods'][item['method']]
            mitigation = f"（限制应对：{item['mitigation']}）" if item['mitigation'] else ''
            parts.append(f"- **{assessment['method_cn']}**（余量 {assessment['depth_margin']:.2f}×，成本{assessment['relative_cost']}）：{item['rationale']}{mitigation}")
    excluded = [item for item in plan['items'] if item['role'] == EXCLUDED]
    if excluded:
        parts.extend(['', '### 不建议采用的方法', ''])
        for item in excluded:
            assessment = bundle['methods'][item['method']]
            if not assessment['feasible']:
                label = '深度不足'
            elif assessment['suitability'] == '不适用':
                label = '物性不匹配'
            else:
                label = f"判定为{assessment['suitability']}"
            parts.append(f"- **{assessment['method_cn']}**（{label}）：{item['rationale']}")
    parts.extend(['', '## 四、采集参数（主方法）', '', _acquisition_table(bundle, design)])
    parts.extend(['', '## 五、外业布置与工作量', '', _design_table(design)])
    if design.get('basis'):
        parts.extend(['', '估算依据：', ''])
        parts.extend((f'- {line}' for line in design['basis']))
    parts.extend(['', '## 六、风险与对策', '', '| 风险 | 影响 | 对策 |', '|---|---|---|'])
    for risk in plan['risks']:
        parts.append(f"| {_cell(risk['risk'])} | {_cell(risk['impact'])} | {_cell(risk['response'])} |")
    parts.extend(['', '## 七、验证与待补资料', '', '**验证措施**：', ''])
    parts.extend((f'- {item}' for item in plan['verification']))
    if plan['missing_information']:
        parts.extend(['', '**待补资料**：', ''])
        parts.extend((f'- {item}' for item in plan['missing_information']))
    if warnings:
        parts.extend(['', '**系统提示**：', ''])
        parts.extend((f'- {item}' for item in warnings))
    parts.extend(['', '## 八、课程依据', ''])
    parts.extend(_evidence_section(evidence))
    parts.extend(['', '## 九、性质说明', ''])
    parts.append(DISCLAIMER)
    parts.extend(['', '---', '_数值来源：Dify 代码节点（与本地 `analysis/` 同源，逐字段对拍通过）；模型只负责选择方案角色与撰写理由。_'])
    return '\n'.join(parts).strip() + '\n'

def render_clarification(bundle_conditions_view, questions):
    known = []
    view = bundle_conditions_view or {}
    for key, label in (('target', '探测目标'), ('medium', '主要介质'), ('depth', '目标埋深')):
        if view.get(key):
            known.append(f'{label}：{view[key]}')
    known_text = '、'.join(known) if known else '暂无'
    lines = ['# 需要补充信息', '', '我是「工程物探勘察方案推荐」助手：从八种工程物探方法（GPR／直流电阻率／面波／地震折射／磁法／FDEM／TEM／DAS）里比选方案，按物理关系反算采集参数，并估算外业工作量。', '', f'目前已确认：{known_text}。还缺关键字段，无法给出可靠方案——物探方法的选择高度依赖目标物性差异与埋深，缺项时给出的方案容易变成「按名称套方法」。', '', '## 请补充', '']
    lines.extend((f'{index}. {question}' for index, question in enumerate(questions, start=1)))
    lines.extend(['', '## 补齐后我会做什么', '', '1. 用八种方法的深度-分辨率-成本评估表逐项校核；', '2. 按物理关系反算排列长度、电极距、天线频率等采集参数；', '3. 生成方案并用规则校验器自检，冲突时自动修正。'])
    return '\n'.join(lines) + '\n'

def _normalize_evidence(evidence):
    if evidence is None:
        return []
    if isinstance(evidence, str):
        try:
            evidence = json.loads(evidence)
        except json.JSONDecodeError:
            return []
    if isinstance(evidence, dict):
        evidence = evidence.get('result', [])
    items = []
    for item in evidence or []:
        if isinstance(item, dict):
            items.append({'content': str(item.get('content') or ''), 'score': item.get('score'), 'title': str(item.get('title') or '')})
    return items

def main(assess_json: str, llm_json: str='', evidence=None) -> dict:
    bundle = json.loads(assess_json) if assess_json else {}
    if bundle.get('status') == 'need_more_info' or not bundle.get('methods'):
        return {'answer_md': render_clarification(bundle.get('conditions_view'), bundle.get('questions') or []), 'mode': 'clarification', 'violations': '[]'}
    conditions = bundle.get('conditions') or {}
    evidence_items = _normalize_evidence(evidence)
    draft = parse_draft(llm_json)
    if draft is None:
        draft = fallback_plan(bundle)
        mode = 'degraded'
        warnings = list(bundle.get('warnings') or []) + ['模型输出无法解析为合法的方案 JSON，已改用规则方案']
        violations = []
    else:
        violations = verify(draft, conditions, bundle)
        if has_errors(violations):
            draft = fallback_plan(bundle)
            mode = 'degraded'
            errors = [item for item in violations if item['severity'] == 'error']
            warnings = list(bundle.get('warnings') or []) + [f'模型方案未通过校验（{len(errors)} 处 error），已改用规则方案']
        else:
            mode = 'agent'
            warnings = list(bundle.get('warnings') or []) + [f"[{item['code']}] {item['message']}" for item in violations if item['severity'] == 'warning']
    design = bundle.get('design') or {}
    answer = render(draft, bundle, conditions, design, evidence_items, warnings, mode == 'degraded')
    return {'answer_md': answer, 'mode': mode, 'violations': json.dumps(violations, ensure_ascii=False)}
BUILD = '2026-11-17.2'
