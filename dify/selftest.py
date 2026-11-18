# -*- coding: utf-8 -*-
"""本地自测：三个代码节点串起来跑一遍，不需要 Dify。

    backend\\.venv\\Scripts\\python.exe dify\\selftest.py

为什么单独放这个文件：
Dify 的代码节点里**不能留** `if __name__ == "__main__":` 自测块——沙箱执行时
`__name__` 可能就是 `"__main__"`，那段代码会被真的跑起来，把输出搞乱
（典型症状：数据处理显示 `{}`、报 `Not all output parameters are validated.`）。
所以三个节点文件现在只留"定义 + main()"，自测挪到这里。
"""

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "backend" / "src"))


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


assess_node = load("code_node_assess_slim")
evidence_node = load("code_node_evidence")
finalize_node = load("code_node_finalize")

DECLARED_ASSESS = {
    "status",
    "assess_json",
    "prompt_input",
    "conditions_json",
    "clarification_md",
}

SAMPLES = (
    "场地为厚层黏土（饱水、低阻），需要追踪地下水污染羽的分布范围与运移通道，目标埋深约 5~12 m。"
    "场地地表为农田，无重要金属设施，但周边有灌溉井和民房。",
    "城市浅层场地，地层以填土为主，需要在道路和小区绿化带内查找地下金属与混凝土管线，埋深 1~3 m。"
    "地表有钢筋混凝土地面、围栏、路灯和车辆等人文干扰，附近还有 10 kV 电力线。",
    "滨海软土场地，地下水位约 1 m，需要评估地震液化风险，获取 0~20 m 浅层横波速度结构。"
    "场地为开阔空地，允许布置较长排列，附近有轻微交通振动。",
    "山区路基工程，围岩为灰岩，需要探测地下溶洞与空洞，埋深 4~15 m。"
    "地表为碎石覆盖、地形起伏较大，附近有公路施工机械作业。",
    "我想做个物探。",
)

FAKE_EVIDENCE = [
    {
        "content": (
            "08_electrical#80｜8.2.10 Applications of resistivity surveying｜"
            "《An Introduction to Geophysical Exploration》(3rd ed., 2002)｜p.196｜教材原文\n"
            "[p.196] Resistivity surveying is widely applied to engineering and "
            "environmental investigations, including the detection of cavities in karst terrain."
        ),
        "score": 0.52,
    }
]


def main() -> int:
    problems = []
    for index, sample in enumerate(SAMPLES, start=1):
        result = assess_node.main(sample)
        keys_ok = set(result) == DECLARED_ASSESS
        if not keys_ok:
            problems.append(f"#{index} 返回键与声明不一致：{sorted(result)}")

        status = result["status"]
        if status == "need_more_info":
            print(f"#{index} 追问分支 | 返回键一致={keys_ok} | 正文 {len(result['clarification_md'])} 字符")
            continue

        bundle = json.loads(result["assess_json"])
        primary = "、".join(bundle["recommended_primary"]) or "无"
        evidence = evidence_node.main(FAKE_EVIDENCE)
        draft = finalize_node.fallback_plan(bundle)
        out = finalize_node.main(
            result["assess_json"], json.dumps(draft, ensure_ascii=False), FAKE_EVIDENCE
        )
        print(
            f"#{index} 方案分支 | 返回键一致={keys_ok} | 主方法 {primary} "
            f"| 回信 {len(out['answer_md'])} 字符 | mode={out['mode']} "
            f"| 证据 {len(evidence['evidence_text'])} 字符"
        )
        if out["mode"] != "agent":
            problems.append(f"#{index} 规则草案应为 agent，实际 {out['mode']}")
        if bundle["design"]["primary_method"] and bundle["design"]["total_line_km"] <= 0:
            problems.append(f"#{index} 外业设计缺失")

    if problems:
        print("\n发现问题：")
        for item in problems:
            print(" -", item)
        return 1
    print("\nSELFTEST OK：五个样例全部跑通，返回键与声明完全一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
