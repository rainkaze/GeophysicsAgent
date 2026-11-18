# -*- coding: utf-8 -*-
"""两端对拍：本地 `analysis/` 与 Dify 代码节点，必须**逐字段相同**。

用途
----
课程项目的核心卖点是"同一套判据、两种呈现"。只要有任何一个数字不同，
答辩时就会被问住。这个脚本把两边放在同一组输入上跑，逐字段比对，
把差异打印出来；只有全部一致才打印 `PARITY OK`。

跑法
----
    cd geophysics_agent_demo2
    backend\\.venv\\Scripts\\python.exe dify\\parity_test.py

覆盖三层
--------
1. **条件抽取**：本地 `intake.extract_conditions` vs 节点 `extract_conditions`
2. **八方法评估**：7 目标 × 7 介质 × 6 埋深 × 3 干扰组合（共 882 组）
3. **内置场景**：4 个演示场景的完整评估（含追问分支）
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "src"))


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


node = _load("dify_assess", "dify/code_node_assess_slim.py")
finalize = _load("dify_finalize", "dify/code_node_finalize.py")

from geophysics_agent.agent.intake import extract_conditions as local_extract  # noqa: E402
from geophysics_agent.agent.planner import fallback_plan as local_fallback  # noqa: E402
from geophysics_agent.agent.renderer import render as local_render  # noqa: E402
from geophysics_agent.agent.verifier import verify as local_verify  # noqa: E402
from geophysics_agent.analysis.calculator import assess as local_assess  # noqa: E402
from geophysics_agent.domain.conditions import DepthRange, SiteConditions  # noqa: E402
from geophysics_agent.domain.enums import Interference, Medium, Method, Role, Target  # noqa: E402
from geophysics_agent.domain.plan import PlanDraft, SurveyPlan  # noqa: E402
from geophysics_agent.domain.scenarios import SCENARIOS  # noqa: E402

#: 节点里的干扰代码 → 本地枚举（本地枚举值是中文）
INTERFERENCE_MAP = {
    "rebar": Interference.REBAR,
    "powerline": Interference.POWERLINE,
    "traffic": Interference.TRAFFIC,
    "machinery": Interference.MACHINERY,
    "fence": Interference.FENCE,
    "vibration": Interference.VIBRATION,
    "terrain": Interference.TERRAIN,
}

FAILURES: list[str] = []


def check(label: str, local_value, node_value) -> None:
    if local_value != node_value:
        FAILURES.append(f"{label}\n    本地={local_value!r}\n    节点={node_value!r}")


def compare_bundles(tag: str, conditions: SiteConditions, node_conditions: dict) -> None:
    bundle = local_assess(conditions)
    got = node.assess(node_conditions)

    check(f"{tag} target_cn", bundle.target_cn, got["target_cn"])
    check(f"{tag} medium_cn", bundle.medium_cn, got["medium_cn"])
    check(f"{tag} design_depth", bundle.design_depth_m, got["design_depth_m"])
    check(f"{tag} depth_range", bundle.depth_range, got["depth_range"])
    check(f"{tag} primary", [m.value for m in bundle.recommended_primary], got["recommended_primary"])
    check(f"{tag} support", [m.value for m in bundle.recommended_support], got["recommended_support"])
    check(f"{tag} infeasible", [m.value for m in bundle.infeasible], got["infeasible"])
    check(f"{tag} warnings", bundle.warnings, got["warnings"])
    check(f"{tag} contrast", bundle.target_contrast, got["target_contrast"])
    check(f"{tag} note", bundle.target_note, got["target_note"])

    for method in node.METHOD_ORDER:
        a = bundle.methods[Method(method)]
        b = got["methods"][method]
        for field in (
            "max_depth_m",
            "depth_margin",
            "depth_check",
            "feasible",
            "vertical_resolution_m",
            "resolution_basis",
            "station_spacing_m",
            "array_length_m",
            "relative_cost",
            "cost_index",
            "physics_basis",
            "deployment_requirement",
            "limitations",
            "interference_notes",
        ):
            check(f"{tag} {method}.{field}", getattr(a, field), b[field])
        check(f"{tag} {method}.suitability", a.suitability.value, b["suitability"])
        check(f"{tag} {method}.reason", a.suitability_reason, b["suitability_reason"])
        check(f"{tag} {method}.acquisition", a.acquisition.items, b["acquisition"])

    d, e = bundle.design, got["design"]
    for field in (
        "main_line_length_m",
        "line_count",
        "cross_line_spacing_m",
        "total_line_km",
        "station_count",
        "relative_cost_index",
        "cost_band",
        "basis",
    ):
        check(f"{tag} design.{field}", getattr(d, field), e[field])
    check(
        f"{tag} design.primary_method",
        d.primary_method.value if d.primary_method else None,
        e["primary_method"],
    )


def main() -> int:
    # ---------------------------------------------------------- 1. 条件抽取
    samples = [scenario.query for scenario in SCENARIOS] + [
        "灰岩场地，目标埋深 20~30 m，找溶洞，有钢筋和高压线干扰",
        "埋深 30 m，找管线，场地 300 m，预算有限",
        "基岩场地，查明覆盖层厚度与基岩面埋深，埋深 0~20 m，无重要金属设施",
        "软土场地 20 m 深度内做液化判别，附近有轻微交通振动",
        "我想做个物探",
    ]
    for index, text in enumerate(samples):
        local = local_extract(text)
        got = node.extract_conditions(text)
        check(
            f"extract[{index}].target",
            local.target.value if local.target else None,
            got["target"],
        )
        check(
            f"extract[{index}].medium",
            local.medium.value if local.medium else None,
            got["medium"],
        )
        check(f"extract[{index}].depth", str(local.depth) if local.depth else None,
              f"{got['depth']['min_m']:g}~{got['depth']['max_m']:g} m" if got["depth"] and got["depth"]["min_m"] != got["depth"]["max_m"] else (
                  f"{got['depth']['max_m']:g} m" if got["depth"] else None))
        check(
            f"extract[{index}].surface",
            local.surface.value if local.surface else None,
            node.SURFACE_CN.get(got["surface"]) if got["surface"] else None,
        )
        check(
            f"extract[{index}].interference",
            [item.value for item in local.interference],
            [node.INTERFERENCE_CN[i] for i in got["interference"]],
        )

    # ---------------------------------------------------------- 2. 评估矩阵
    depths = ((1, 1), (2, 4), (4, 12), (8, 20), (15, 30), (25, 40))
    interference_sets = ((), ("rebar",), ("powerline", "fence"))
    total = 0
    for target in Target:
        for medium in Medium:
            for low, high in depths:
                for interference in interference_sets:
                    conditions = SiteConditions(
                        target=target,
                        medium=medium,
                        depth=DepthRange(min_m=float(low), max_m=float(high)),
                        interference=[INTERFERENCE_MAP[i] for i in interference],
                    )
                    node_conditions = {
                        "target": target.value,
                        "medium": medium.value,
                        "depth": {"min_m": float(low), "max_m": float(high)},
                        "surface": None,
                        "interference": list(interference),
                        "budget": None,
                        "site_length_m": None,
                        "accuracy": None,
                        "free_text": "",
                    }
                    compare_bundles(
                        f"[{target.value}/{medium.value}/{low}-{high}/{'+'.join(interference) or '-'}]",
                        conditions,
                        node_conditions,
                    )
                    total += 1

    # ---------------------------------------------------------- 3. 内置场景
    for scenario in SCENARIOS:
        local = local_extract(scenario.query)
        compare_bundles(f"[场景{scenario.sid}]", local, node.extract_conditions(scenario.query))

    # ---------------------------------------------------------- 4. 校验 + 兜底
    checks = 0
    for scenario in SCENARIOS:
        local_conditions = local_extract(scenario.query)
        node_conditions = node.extract_conditions(scenario.query)
        local_bundle = local_assess(local_conditions)
        node_bundle = node.assess(node_conditions)
        tag = f"[场景{scenario.sid}]"

        local_plan = local_fallback(local_bundle)
        node_plan = finalize.fallback_plan(node_bundle)
        check(f"{tag} fallback.summary", local_plan.summary, node_plan["summary"])
        check(
            f"{tag} fallback.items",
            [(i.method.value, i.role.value, i.rationale, i.mitigation) for i in local_plan.items],
            [(i["method"], i["role"], i["rationale"], i["mitigation"]) for i in node_plan["items"]],
        )
        check(
            f"{tag} fallback.risks",
            [(r.risk, r.impact, r.response) for r in local_plan.risks],
            [(r["risk"], r["impact"], r["response"]) for r in node_plan["risks"]],
        )
        check(f"{tag} fallback.verification", local_plan.verification, node_plan["verification"])

        # 多组草案：规则方案 / 主方法换成不可行方法 / 去掉 mitigation / 验证措施不合格
        drafts = [local_plan]
        infeasible = [
            m
            for m in node.METHOD_ORDER
            if not local_bundle.methods[Method(m)].feasible
        ]
        if infeasible:
            swapped = local_plan.model_copy(deep=True)
            for item in swapped.items:
                item.role = Role.EXCLUDED
            swapped.items[0].method = Method(infeasible[0])
            swapped.items[0].role = Role.PRIMARY
            drafts.append(swapped)
        stripped = local_plan.model_copy(deep=True)
        for item in stripped.items:
            item.mitigation = None
        stripped.verification = ["仔细核对数据"]
        stripped.risks = stripped.risks[:1]
        drafts.append(stripped)

        for index, draft in enumerate(drafts):
            local_violations = local_verify(draft, local_conditions, local_bundle)
            node_violations = finalize.verify(
                {
                    "summary": draft.summary,
                    "items": [
                        {
                            "method": item.method.value,
                            "role": item.role.value,
                            "rationale": item.rationale,
                            "mitigation": item.mitigation,
                        }
                        for item in draft.items
                    ],
                    "risks": [{"risk": r.risk, "impact": r.impact, "response": r.response} for r in draft.risks],
                    "verification": list(draft.verification),
                    "missing_information": list(draft.missing_information),
                },
                node_conditions,
                node_bundle,
            )
            check(
                f"{tag} verify[{index}]",
                [(v.code, v.severity, v.message) for v in local_violations],
                [(v["code"], v["severity"], v["message"]) for v in node_violations],
            )
            checks += 1

        # 渲染：两边正文里出现的数字必须一致
        local_plan_obj = SurveyPlan(
            summary=local_plan.summary,
            items=local_plan.items,
            risks=local_plan.risks,
            verification=local_plan.verification,
            missing_information=local_plan.missing_information,
        )
        local_md = local_render(
            plan=local_plan_obj,
            conditions=local_conditions,
            bundle=local_bundle,
            design=local_bundle.design,
            evidence=[],
            quality="empty",
            warnings=[],
        )
        node_md = finalize.render(
            node_plan,
            node_bundle,
            node_conditions,
            node_bundle["design"],
            [],
            [],
            False,
        )
        numbers = []
        primary = node_plan["items"][0]["method"] if node_plan["items"][0]["role"] == "主方法" else None
        if primary:
            numbers.extend(node_bundle["methods"][primary]["acquisition"].values())
        design = node_bundle["design"]
        numbers.extend(
            [
                f"{design['total_line_km']:g} km",
                f"{design['station_count']} 点",
                f"{design['relative_cost_index']:.1f}",
            ]
        )
        for value in numbers:
            check(f"{tag} render.local 含 {value!r}", True, value in local_md)
            check(f"{tag} render.node 含 {value!r}", True, value in node_md)

    # ---------------------------------------------------------- 5. 多轮合并 + 追问
    base = SiteConditions(
        target=Target.KARST,
        medium=Medium.LIMESTONE,
        depth=DepthRange(min_m=4.0, max_m=15.0),
        interference=[Interference.MACHINERY],
    )
    base_node = node.extract_conditions("灰岩场地，找溶洞，埋深 4~15 m，附近有施工机械")
    for text in ("埋深改成 60 m 呢？", "这里是软土场地", "再考虑一下预算有限", "换成砂土，埋深 8 m"):
        local_merged = base.merge(local_extract(text))
        node_merged = node.merge_conditions(base_node, node.extract_conditions(text))
        check(
            f"merge[{text}].target",
            local_merged.target.value if local_merged.target else None,
            node_merged["target"],
        )
        check(
            f"merge[{text}].medium",
            local_merged.medium.value if local_merged.medium else None,
            node_merged["medium"],
        )
        check(
            f"merge[{text}].depth",
            f"{local_merged.depth.min_m:g}-{local_merged.depth.max_m:g}" if local_merged.depth else None,
            f"{node_merged['depth']['min_m']:g}-{node_merged['depth']['max_m']:g}"
            if node_merged["depth"]
            else None,
        )
        check(
            f"merge[{text}].interference",
            [item.value for item in local_merged.interference],
            [node.INTERFERENCE_CN[i] for i in node_merged["interference"]],
        )

    from geophysics_agent.agent.renderer import render_clarification as local_clarify  # noqa: E402

    vague = local_extract("我想做个物探")
    check(
        "clarification 正文",
        local_clarify(vague, __import__("geophysics_agent.agent.intake", fromlist=["x"]).build_questions(vague)),
        node.render_clarification(node.extract_conditions("我想做个物探"), node.build_questions(node.extract_conditions("我想做个物探"))),
    )

    # ---------------------------------------------------------- 6. 端到端
    scenario = SCENARIOS[0]
    start = node.main(scenario.query)
    node_bundle = json.loads(start["assess_json"])
    good = finalize.fallback_plan(node_bundle)
    out = finalize.main(start["assess_json"], json.dumps(good, ensure_ascii=False), [])
    check("e2e 规则草案 → agent", "agent", out["mode"])

    bad = json.loads(json.dumps(good))
    for item in bad["items"]:
        item["role"] = "不建议采用"
    for item in bad["items"]:
        if item["method"] == "gpr":  # 场景 1 里 GPR 深度不可行
            item["role"] = "主方法"
    out = finalize.main(start["assess_json"], json.dumps(bad, ensure_ascii=False), [])
    check("e2e 坏草案(主方法深度不可行 + 排除首选方法) → degraded", "degraded", out["mode"])

    out = finalize.main(start["assess_json"], "这不是 JSON", [])
    check("e2e 非 JSON → degraded", "degraded", out["mode"])

    out = finalize.main(node.main("我想做个物探")["assess_json"], "", [])
    check("e2e 条件不全 → clarification", "clarification", out["mode"])

    print(f"评估矩阵：{total} 组 × 8 方法 × 19 字段；校验对拍 {checks} 组草案；端到端 4 条路径")
    if FAILURES:
        print(f"\n不一致 {len(FAILURES)} 处：\n")
        for item in FAILURES[:40]:
            print(" -", item)
        print("\nPARITY FAILED")
        return 1
    _write_report()
    print("PARITY OK：两端逐字段一致（对照表已写入 dify/parity-report.md）")
    return 0


def _write_report() -> None:
    """生成答辩可直接放的"两端对照表"。"""
    rows = []
    for scenario in SCENARIOS:
        local_conditions = local_extract(scenario.query)
        bundle = local_assess(local_conditions)
        node_result = node.main(scenario.query)
        node_bundle = json.loads(node_result["assess_json"])
        primary = bundle.recommended_primary[0]
        design = bundle.design
        acq = bundle.methods[primary].acquisition.items
        rows.append(
            "| {sid} | {target}／{medium}／{depth} | {method} | {acq} | {km:g} km／{stations} 点／指数 {cost:.1f}（{band}） | ✅ |".format(
                sid=scenario.sid,
                target=bundle.target_cn,
                medium=bundle.medium_cn,
                depth=bundle.depth_range,
                method=bundle.methods[primary].method_cn,
                acq="；".join(f"{k} {v}" for k, v in acq.items()),
                km=design.total_line_km,
                stations=design.station_count,
                cost=design.relative_cost_index,
                band=design.cost_band,
            )
        )
        # 顺带确认节点侧一致（不一致时 parity 已经失败，这里只做事后断言）
        assert node_bundle["recommended_primary"] == [primary.value]
        assert node_bundle["design"]["relative_cost_index"] == design.relative_cost_index

    text = "\n".join(
        [
            "# 两端对照表（由 `dify/parity_test.py` 自动生成）",
            "",
            "本地 `analysis/` 与 Dify 代码节点对同一输入的结果，逐字段一致：",
            "",
            "| 场景 | 目标／介质／埋深 | 主方法 | 采集参数（主方法） | 外业工作量 | 一致 |",
            "|---|---|---|---|---|---|",
            *rows,
            "",
            "> 表格由脚本生成，改判据后重跑 `parity_test.py` 即更新。",
            "> 端到端覆盖面：882 组条件 × 8 方法 × 19 字段 + 11 组草案校验 + 4 条降级路径。",
        ]
    )
    (ROOT / "dify" / "parity-report.md").write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
