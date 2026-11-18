# -*- coding: utf-8 -*-
"""把三个代码节点压成 `*_slim.py`（给 Dify 粘贴用），并自动对拍语义不变。

为什么需要
----------
Dify 的代码框对超大粘贴会"粘了但没生效"（症状：`Not all output parameters
are validated.`，输出恒为 `{}`）。完整版大小：

    code_node_assess.py     62,257 字节 / 1620 行   ← 实测会被吞
    code_node_finalize.py   30,350 字节 /  753 行
    code_node_evidence.py    2,617 字节 /   69 行

瘦身只去掉注释、文档字符串、空行，**逻辑一字不动**，并当场对拍验证：
assess 跑 882 组矩阵、finalize 跑 3 种草案、evidence 跑 2 种输入。

用法
----
    backend\\.venv\\Scripts\\python.exe dify\\build_slim.py

改完任何一个完整版后都要重跑；`parity_test.py` / `selftest.py` 测的是瘦身版
（也就是 Dify 里真正跑的那份）。
"""

import ast
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGETS = ("code_node_assess", "code_node_finalize", "code_node_evidence")


def strip_docstrings(tree: ast.Module) -> ast.Module:
    if (
        tree.body
        and isinstance(tree.body[0], ast.Expr)
        and isinstance(tree.body[0].value, ast.Constant)
        and isinstance(tree.body[0].value.value, str)
    ):
        tree.body.pop(0)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Module)):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                body.pop(0)
                if not body:
                    body.append(ast.Pass())
    return tree


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def build() -> int:
    problems = 0
    for stem in TARGETS:
        src = HERE / f"{stem}.py"
        dst = HERE / f"{stem}_slim.py"
        tree = strip_docstrings(ast.parse(src.read_text(encoding="utf-8")))
        code = ast.unparse(ast.fix_missing_locations(tree)) + "\n"
        dst.write_text(code, encoding="utf-8")
        print(
            f"{stem:22s} {src.stat().st_size:>7,} B / {len(src.read_text(encoding='utf-8').splitlines()):>5} 行"
            f"  →  {dst.stat().st_size:>7,} B / {len(code.splitlines()):>5} 行"
        )
    print()
    return problems


def check_assess() -> int:
    full = load("_a_full", HERE / "code_node_assess.py")
    slim = load("_a_slim", HERE / "code_node_assess_slim.py")
    targets = ["plume", "utility", "karst", "aquifer", "uxo", "liquefaction", "site_investigation"]
    mediums = ["clay", "silt", "sand", "fill", "limestone", "bedrock", "soft_soil"]
    depths = [(1, 1), (2, 4), (4, 12), (8, 20), (15, 30), (25, 40)]
    inters = [[], ["rebar"], ["powerline", "fence"]]
    bad = total = 0
    for target in targets:
        for medium in mediums:
            for low, high in depths:
                for interference in inters:
                    conditions = {
                        "target": target,
                        "medium": medium,
                        "depth": {"min_m": float(low), "max_m": float(high)},
                        "surface": None,
                        "interference": interference,
                        "budget": None,
                        "site_length_m": None,
                        "accuracy": None,
                        "free_text": "",
                    }
                    left = json.dumps(full.assess(conditions), ensure_ascii=False, sort_keys=True)
                    right = json.dumps(slim.assess(conditions), ensure_ascii=False, sort_keys=True)
                    total += 1
                    bad += 1 if left != right else 0
    print(f"assess  对拍 {total} 组 → 不一致 {bad} 组")
    return bad


def check_finalize() -> int:
    full = load("_f_full", HERE / "code_node_finalize.py")
    slim = load("_f_slim", HERE / "code_node_finalize_slim.py")
    assess = load("_a_slim2", HERE / "code_node_assess_slim.py")

    query = "山区路基工程，围岩为灰岩，需要探测地下溶洞与空洞，埋深 4~15 m。地表为碎石覆盖、地形起伏较大。"
    result = assess.main(query)
    bundle = json.loads(result["assess_json"])
    evidence = [
        {
            "content": "08_electrical#80｜8.2.10 Applications of resistivity surveying｜教材｜p.196｜教材原文\n"
            "[p.196] Resistivity surveying is applied to karst cavities.",
            "score": 0.52,
        }
    ]
    good = json.dumps(full.fallback_plan(bundle), ensure_ascii=False)
    bad_draft = json.loads(good)
    for item in bad_draft["items"]:
        item["role"] = "不建议采用"
    for item in bad_draft["items"]:
        if item["method"] == "gpr":
            item["role"] = "主方法"

    cases = [
        ("规则草案→agent", result["assess_json"], good, evidence),
        ("坏草案→degraded", result["assess_json"], json.dumps(bad_draft, ensure_ascii=False), evidence),
        ("非 JSON→degraded", result["assess_json"], "这不是 JSON", evidence),
        ("空证据", result["assess_json"], good, []),
    ]
    bad = 0
    for name, assess_json, llm_json, ev in cases:
        left = full.main(assess_json, llm_json, ev)
        right = slim.main(assess_json, llm_json, ev)
        same = left == right
        bad += 0 if same else 1
        print(f"finalize {name:18s} 一致={same} mode={right['mode']}")
    return bad


def check_evidence() -> int:
    full = load("_e_full", HERE / "code_node_evidence.py")
    slim = load("_e_slim", HERE / "code_node_evidence_slim.py")
    cases = [
        [],
        [{"content": "ERT-001｜电阻率多解性｜课件｜p.5｜待核对\n正文一句。", "score": 0.61}],
    ]
    bad = 0
    for index, payload in enumerate(cases):
        left, right = full.main(payload), slim.main(payload)
        same = left == right
        bad += 0 if same else 1
        print(f"evidence 用例{index}            一致={same}")
    return bad


def main() -> int:
    sys.path.insert(0, str(HERE.parent / "backend" / "src"))
    build()
    problems = check_assess() + check_finalize() + check_evidence()
    print()
    if problems:
        print(f"SLIM FAILED：{problems} 处不一致")
        return 1
    print("SLIM OK：三个节点瘦身版与原版语义完全一致")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
