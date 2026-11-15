"""kb.py 查询：依赖 / 约束 / 替代 / 决策链。所有输出都是图上已登记的边，不做推断。

推理纪律（ontology §3.3）写死在代码里：
- 只有 TRANSITIVE 关系做多跳，其余一跳即止；
- constrains 只沿 is_a 向下继承（父受约束 ⇒ 子受约束），不反推；
- 反向查询只列出"谁指向它"这一事实，不推断因果。
"""
import onto_rules as R

DEP_RELS = ("depends_on", "part_of", "implemented_by", "is_a")
REL_ZH = {"depends_on": "依赖", "part_of": "属于", "implemented_by": "由…实现", "is_a": "是一种",
          "constrains": "约束", "calibrated_by": "阈值标定于", "applies_to": "适用于",
          "conflicts_with": "冲突", "supersedes": "替代", "measured_by": "度量指标",
          "produces": "产出", "evidence_for": "证据支撑", "chooses": "选择",
          "rejects": "否决", "based_on": "依据"}
NONE = "（库内无此关系登记）"


def _edge_line(g, d, e, reverse=False):
    other = e["src"] if reverse else e["dst"]
    extra = []
    if e["modality"] in ("possible", "instance"):
        extra.append(f"[{e['modality']}]")
    if e["qualifier"]:
        extra.append(f"（{e['qualifier']}）")
    if e["note"]:
        extra.append(f"— {e['note']}")
    arrow = "⇐" if reverse else "→"
    return f"{'  ' * d}{arrow} {REL_ZH.get(e['rel'], e['rel'])} {g.label(other)} {' '.join(extra)}".rstrip()


def deps(g, name, reverse=False):
    """谁依赖谁。

    正向（reverse=False）：它依赖什么 —— 沿 DEP_RELS 出边，仅传递关系多跳。
    反向（reverse=True）：谁依赖它（影响面）—— 沿同一批关系入边，不推断因果。
    """
    lines = [f"## {'影响面（谁依赖它）' if reverse else '依赖链'}：{g.label(name)}"]
    for rel in DEP_RELS:
        hits = g.closure(name, rel, reverse=reverse)
        if hits:
            hop = "多跳" if rel in R.TRANSITIVE else "一跳"
            lines.append(f"- {rel}（{hop}）")
            lines += [_edge_line(g, d, e, reverse) for d, e in hits]
    return "\n".join(lines) if len(lines) > 1 else lines[0] + "\n" + NONE


def _ancestors(g, name):
    return [name] + [e["dst"] for _, e in g.closure(name, "is_a")]


def constraints(g, name):
    """谁约束它（含沿 is_a 继承）+ 它约束谁 + 冲突 / 标定 / 适用。"""
    lines = [f"## 约束关系：{g.label(name)}"]
    got = []
    for anc in _ancestors(g, name):
        for e in g.inc(anc, "constrains"):
            via = "" if anc == name else f"（继承自上位类 {anc}）"
            got.append(f"  ⇐ 受约束于 {g.label(e['src'])}{via}")
    if got:
        lines += ["- 谁约束它"] + got
    sections = [("它约束谁", "constrains", False), ("阈值标定于", "calibrated_by", False),
                ("适用于", "applies_to", False), ("冲突", "conflicts_with", None)]
    for title, rel, rev in sections:
        es = g.out(name, rel) + (g.inc(name, rel) if rev is None else [])
        if es:
            lines.append(f"- {title}")
            for e in es:
                other = e["dst"] if e["src"] == name else e["src"]
                detail = []
                if e["modality"] != "universal":
                    detail.append(f"[{e['modality']}]")
                if e["qualifier"]:
                    detail.append(f"（{e['qualifier']}）")
                if e["note"]:
                    detail.append(f"— 裁定：{e['note']}")
                lines.append(f"  → {g.label(other)} {' '.join(detail)}".rstrip())
    return "\n".join(lines) if len(lines) > 1 else lines[0] + "\n" + NONE


def lineage(g, name):
    """谁替代了谁：向上找新版、向下找旧版，带失效日期。"""
    def fmt(n):
        if g.nodes[n]["placeholder"]:
            return g.label(n)
        fm = g.nodes[n]["fm"]
        return f"{g.label(n)} 状态={fm.get('status', '-')} valid_until={fm.get('valid_until') or '-'}"
    newer = g.closure(name, "supersedes", reverse=True)
    older = g.closure(name, "supersedes")
    lines = [f"## 替代链：{fmt(name)}"]
    if newer:
        lines += ["- 被谁替代（新版）"] + [f"{'  ' * d}⇐ {fmt(e['src'])}" for d, e in newer]
    if older:
        lines += ["- 它替代了谁（旧版）"] + [f"{'  ' * d}→ {fmt(e['dst'])}" for d, e in older]
    return "\n".join(lines) if len(lines) > 1 else lines[0] + "\n" + NONE


def chain(g, name):
    """完整决策链 Markdown。"""
    n = g.nodes[name]
    if n["l2"] != R.DECISION:
        raise ValueError(f"{name} 不是决策卡（type={n['l2']}）")
    fm = n["fm"]
    L = [f"# 决策链 · {name}", "",
         f"- 问题：{fm.get('question')}",
         f"- 状态：{fm.get('status')} ｜ 决策日：{fm.get('decided_at') or '-'} ｜ 复核：{fm.get('review_at') or '-'} ｜ 责任人：{fm.get('owner')}",
         ""]

    def block(title, es, pick, with_note=False):
        if not es:
            return
        L.append(f"## {title}")
        for e in es:
            note = f" —— {e['note']}" if with_note and e["note"] else ""
            L.append(f"- {g.label(pick(e))}{note}")
        L.append("")

    block("✔ 选择", g.out(name, "chooses"), lambda e: e["dst"])
    block("✘ 否决", g.out(name, "rejects"), lambda e: e["dst"], with_note=True)
    based = g.out(name, "based_on")
    block("依据", based, lambda e: e["dst"])
    block("受约束于", g.inc(name, "constrains"), lambda e: e["src"])
    block("替代了（旧决策）", g.out(name, "supersedes"), lambda e: e["dst"])
    block("已被替代（新决策）", g.inc(name, "supersedes"), lambda e: e["src"])

    deep = []
    for e in based:
        tgt = e["dst"]
        if g.nodes[tgt]["placeholder"]:
            continue
        for rel in ("depends_on", "is_a"):
            deep += [f"- {tgt} {_edge_line(g, d, x).strip()}" for d, x in g.closure(tgt, rel)]
        deep += [f"- {tgt} ⇐ 受约束于 {g.label(x['src'])}" for x in g.inc(tgt, "constrains")]
    if deep:
        L += ["## 依据的上游（依赖 / 上位 / 约束，均为已登记关系）"] + deep + [""]
    srcs = sorted({x for e in g.edges if name in (e["src"], e["dst"]) for x in (e["src"], e["dst"])
                   if not g.nodes[x]["placeholder"]})
    L.append(f"来源卡片 {len(srcs)} 张：" + "、".join(f"[[{s}]]" for s in srcs))
    return "\n".join(L) + "\n"
