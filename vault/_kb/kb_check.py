"""kb.py check：写入前校验（ontology v1.0 §5 必填、§3.3 domain/range、§3.2 治理要求、§8 决策层）。"""
import datetime as dt

import onto_rules as R

KNOWLEDGE_REQUIRED = ("id", "type", "obj_type", "domain", "definition", "modality",
                      "anchors", "evidence_level", "owner")
DECISION_REQUIRED = ("id", "type", "obj_type", "status", "question", "review_at", "owner")
MODALITIES = {"universal", "possible", "instance"}


def _date(s):
    try:
        return dt.date.fromisoformat(s) if s else None
    except ValueError:
        return "bad"


def check(g, today=None):
    """返回 findings: [(level, 卡名, 对象, 说明)]；level ∈ violation / warn。

    顺序固定：解析错误 → 逐卡 → 逐边 → 环。today 只在这里取一次，向下透传。
    """
    today = today or dt.date.today()
    f = list(g.errors)
    for name, n in g.nodes.items():
        if not n["placeholder"]:
            f += _check_card(g, name, n, today)
    for e in g.edges:
        f += _check_edge(g, e)
    for rel, cyc in R.find_cycles([(e["rel"], e["src"], e["dst"]) for e in g.edges]):
        f.append(("violation", cyc[0], " → ".join(cyc), f"{rel} 出现环"))
    return f


# ---------- 逐卡 ----------
def _required(l2):
    if l2 == R.DECISION:
        return DECISION_REQUIRED
    if l2 == "Pattern":  # Pattern 只有一句话定义，不参与 §1 L1 分类
        return tuple(k for k in KNOWLEDGE_REQUIRED if k != "obj_type")
    return KNOWLEDGE_REQUIRED


def _check_card(g, name, n, today):
    fm = n["fm"]
    f = [("violation", name, k, "必填字段缺失") for k in _required(n["l2"]) if not fm.get(k)]
    f += _check_decision(g, name, fm, today) if n["l2"] == R.DECISION else _check_knowledge(g, name, n)
    for k in ("valid_from", "valid_until", "review_at", "decided_at"):
        if _date(fm.get(k)) == "bad":
            f.append(("violation", name, k, f"日期须为 YYYY-MM-DD：{fm.get(k)}"))
    vu = _date(fm.get("valid_until"))
    if vu and vu != "bad" and vu < today and not g.inc(name, "supersedes"):
        f.append(("warn", name, "valid_until", f"已于 {vu} 过期且无替代者，需复核"))
    return f


def _check_knowledge(g, name, n):
    fm, mod, f = n["fm"], n["fm"].get("modality"), []
    if n["l2"] and n["l2"] not in R.L2:
        f.append(("violation", name, f"type={n['l2']}", "不在 L2 五类 / Decision 内"))
    if n["l1"] and n["l1"] not in R.L1_STRICT:
        f.append(("warn", name, f"obj_type={n['l1']}", "不在 §1 八类受控词表内"))
    if mod and mod not in MODALITIES:
        f.append(("violation", name, f"modality={mod}", "非法模态"))
    if mod == "instance" and not fm.get("valid_from"):
        f.append(("violation", name, "valid_from", "instance 事实必须带时间"))
    if not g.touching(name) and n["l2"] != "Pattern":
        f.append(("warn", name, "relations", "无任何 typed 关系（§5 要求至少一条）"))
    return f


def _check_decision(g, name, fm, today):
    """today 必须由 check() 传入：曾硬编码 dt.date.today()，
    导致同一函数内出现两个「今天」，跨日期回归（冻结日期测到期）永远测不出来。"""
    st, f = fm.get("status"), []
    if st and st not in R.DECISION_STATUS:
        f.append(("violation", name, f"status={st}", f"须为 {sorted(R.DECISION_STATUS)}"))
    if st in ("accepted", "superseded"):
        if not g.out(name, "chooses"):
            f.append(("violation", name, "chooses", f"status={st} 必须至少选择一项"))
        if not fm.get("decided_at"):
            f.append(("violation", name, "decided_at", f"status={st} 必须写决策日期"))
    if st == "superseded" and not g.inc(name, "supersedes"):
        f.append(("violation", name, "status", "标为 superseded 但没有任何决策 supersedes 它"))
    ra = _date(fm.get("review_at"))
    if ra and ra != "bad" and st in ("accepted", "proposed") and ra <= today:
        f.append(("warn", name, "review_at", f"{ra} 已到期，需复核"))
    return f


# ---------- 逐边 ----------
NOTE_REQUIRED = {"conflicts_with": "裁定结论", "rejects": "否决理由"}


def _check_edge(g, e):
    src, dst = g.nodes[e["src"]], g.nodes[e["dst"]]
    f = []
    lvl, msg = R.check_edge(e["rel"], src, dst)
    if lvl != "ok":
        f.append((lvl, e["origin"], f"{e['src']} -{e['rel']}-> {e['dst']}", msg))
    if e["rel"] == "measured_by" and dst["l1"] == "指标" and not dst["placeholder"]:
        fm = dst["fm"]
        required = ("metric_numerator", "metric_denominator", "metric_source", "metric_window")
        missing = [key for key in required if not fm.get(key)]
        if missing:
            f.append(("warn", e["origin"], f"{e['src']} -measured_by-> {e['dst']}",
                      f"指标口径字段缺失：{', '.join(missing)}"))
    if e["rel"] == "supersedes" and not dst["placeholder"]:
        if not dst["fm"].get("valid_until"):
            f.append(("violation", e["dst"], "valid_until", f"被 {e['src']} 替代，必须写 valid_until"))
        if dst["l2"] == R.DECISION and dst["fm"].get("status") != "superseded":
            f.append(("violation", e["dst"], "status", "被替代的决策 status 须为 superseded"))
    what = NOTE_REQUIRED.get(e["rel"])
    if what and not e["note"]:
        f.append(("violation", e["origin"], f"{e['declared']} → {e['dst']}", f"缺{what}（写法『[[X]] | 理由』）"))
    return f
