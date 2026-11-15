"""ontology.md v1.0 的机器可执行版本（§2 L2、§1 L1、§3.1–3.3、§8 决策层）。

只编码 ontology.md 里写明的约束。**本文件是关系词表的唯一代码来源**：
改词表只改这里 + vault/_schema/ontology.md，两处版本号必须相等，CI 会断言。
"""
ONTO_VERSION = "1.0"

L2 = {"Concept", "Method", "Tool", "Scenario", "Pattern"}
L1 = {"事实", "规则", "流程", "决策", "案例", "指标", "风险", "行动", "方法", "概念"}
# 注：宽集合保留「方法」「概念」两个历史值，仅为兼容旧卡；严格校验用 L1_STRICT。
L1_STRICT = {"事实", "规则", "流程", "决策", "案例", "指标", "风险", "行动"}

# §3.1 + §3.2 正向关系白名单
FORWARD = {
    "is_a", "part_of", "depends_on", "implemented_by", "applies_to", "measured_by",
    "produces", "supersedes", "conflicts_with", "evidence_for", "constrains", "calibrated_by",
}
# §8 决策关系（源必须是 Decision）
DECISION_RELS = {"chooses", "rejects", "based_on"}
FORWARD |= DECISION_RELS
DECISION = "Decision"
DECISION_STATUS = {"proposed", "accepted", "superseded", "rejected"}
TRANSITIVE = {"is_a", "part_of", "depends_on", "supersedes"}  # §3.3 传递=是
# 反向名 → 正向名（入库统一存正向，方向翻转）
INVERSE = {
    "has_subtype": "is_a", "has_part": "part_of", "required_by": "depends_on",
    "implements": "implemented_by", "applicable_rule": "applies_to", "measures": "measured_by",
    "produced_by": "produces", "superseded_by": "supersedes", "evidenced_by": "evidence_for",
    "constrained_by": "constrains",  # §8.2：Decision 写 constrained_by，入图翻转
}
ACYCLIC = {"is_a", "part_of", "depends_on"}  # §3.3 前置条件"无环"
SYMMETRIC = {"conflicts_with"}


def normalize(rel, src, dst):
    """返回 (正向关系, 源, 目标)；非白名单返回 None。"""
    if rel in FORWARD:
        return rel, src, dst
    if rel in INVERSE:
        return INVERSE[rel], dst, src
    return None


OK = ("ok", "")


class EdgeCtx:
    """一条边两端节点的类型快照，供各关系校验器读取。

    占位节点（自由文本目标）类型未知，只给 warn 不判 violation —— 不能用"未知"去证伪。
    """

    __slots__ = ("sl2", "sl1", "tl2", "tl1", "s_unknown", "t_unknown")

    def __init__(self, s, t):
        self.sl2, self.sl1 = s.get("l2"), s.get("l1")
        self.tl2, self.tl1 = t.get("l2"), t.get("l1")
        self.t_unknown = bool(t.get("placeholder")) and not self.tl2 and not self.tl1
        self.s_unknown = bool(s.get("placeholder")) and not self.sl2 and not self.sl1


def _v_is_a(c):
    if c.t_unknown or c.s_unknown:
        return "warn", "is_a 端点类型未知"
    if c.tl2 not in (c.sl2, "Pattern"):
        return "violation", f"is_a 要求同类或上位类：{c.sl2} → {c.tl2}"
    return OK


def _v_depends_on(c):
    if not c.t_unknown and c.tl2 not in {"Concept", "Method", "Tool"}:
        return "violation", f"depends_on 目标须为 Concept/Method/Tool，实为 {c.tl2}"
    return OK


def _v_implemented_by(c):
    if not c.s_unknown and c.sl2 not in {"Concept", "Method"}:
        return "violation", f"implemented_by 源须为 Concept/Method，实为 {c.sl2}"
    if not c.t_unknown and c.tl2 not in {"Tool", "Method"}:
        return "violation", f"implemented_by 目标须为 Tool/Method，实为 {c.tl2}"
    return OK


def _v_applies_to(c):
    if c.t_unknown:
        return "warn", "applies_to 目标须是 Scenario，当前为未建模自由文本"
    if c.tl2 != "Scenario":
        return "violation", f"applies_to 目标须是 Scenario，实为 {c.tl2}"
    return OK


def _v_measured_by(c):
    if c.t_unknown:
        return "warn", "measured_by 目标须是指标（obj_type=指标）且写口径，当前为自由文本"
    if c.tl1 != "指标":
        return "violation", f"measured_by 目标 obj_type 须为指标，实为 {c.tl1}"
    return OK


def _v_produces(c):
    if not c.s_unknown and c.sl2 not in {"Method", "Tool"}:
        return "violation", f"produces 源须为 Method/Tool，实为 {c.sl2}"
    return OK


def _v_supersedes(c):
    if c.s_unknown or c.t_unknown:
        return "warn", "supersedes 要求同类，端点类型未知；被替代方须填 valid_until"
    if c.sl2 != c.tl2:
        return "violation", f"supersedes 要求同类：{c.sl2} vs {c.tl2}"
    return OK


def _v_evidence_for(c):
    if not c.s_unknown and c.sl1 not in {"案例", "事实"}:
        return "violation", f"evidence_for 源须为 Case/Fact（L1 案例/事实），实为 {c.sl1}"
    return OK


def _v_constrains(c):
    if not c.s_unknown and not (c.sl1 == "规则" or c.sl2 == "Pattern"):
        return "violation", f"constrains 源须为 Rule(L1 规则)/Pattern，实为 {c.sl2}/{c.sl1}"
    return OK


# §3.3 domain → range 校验器表。没列出的关系（part_of / conflicts_with /
# calibrated_by 等）无 domain/range 约束，直接放行。
_VALIDATORS = {
    "is_a": _v_is_a, "depends_on": _v_depends_on, "implemented_by": _v_implemented_by,
    "applies_to": _v_applies_to, "measured_by": _v_measured_by, "produces": _v_produces,
    "supersedes": _v_supersedes, "evidence_for": _v_evidence_for, "constrains": _v_constrains,
}


def check_edge(rel, s, t):
    """按 §3.3 的 domain → range 检查一条正向边，返回 (level, msg)。

    level ∈ {ok, warn, violation}。s / t 为节点 dict：{l2, l1, placeholder}。
    """
    if rel in DECISION_RELS:
        if s.get("l2") != DECISION:
            return "violation", f"{rel} 源须为 Decision，实为 {s.get('l2')}"
        return OK
    fn = _VALIDATORS.get(rel)
    return fn(EdgeCtx(s, t)) if fn else OK


def find_cycles(edges):
    """edges: [(rel, src, dst)]；返回 ACYCLIC 关系上的环列表。"""
    out = []
    for rel in ACYCLIC:
        adj = {}
        for r, a, b in edges:
            if r == rel:
                adj.setdefault(a, []).append(b)
        out += [(rel, cyc) for cyc in _cycles(adj)]
    return out


def _cycles(adj):
    """三色 DFS：遇到「在栈上」(灰) 的节点即成环，返回 [[v, …, v]]。"""
    GRAY, BLACK = 1, 2
    color, stack, found = {}, [], []

    def dfs(u):
        color[u] = GRAY
        stack.append(u)
        for v in adj.get(u, []):
            if color.get(v) == GRAY:
                found.append(stack[stack.index(v):] + [v])
            elif v not in color:
                dfs(v)
        stack.pop()
        color[u] = BLACK

    for n in list(adj):
        if n not in color:
            dfs(n)
    return found
