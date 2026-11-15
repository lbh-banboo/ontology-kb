#!/usr/bin/env python3
"""个人知识库 CLI（ontology v1.0）——零第三方依赖。

  kb.py check                          写入前校验，退出码 1 = 有 violation
  kb.py ask <卡> [关系]                 它依赖什么（可多跳）
  kb.py impact <卡> [关系]              谁依赖它（影响面，反向）
  kb.py constraints <卡>               谁约束它（含 is_a 继承）/ 它约束谁 / 冲突 / 标定
  kb.py lineage <卡>                   谁替代了谁（版本链）
  kb.py chain <决策卡>                  完整决策链（同时写入 _out/chains/）
  kb.py test [tests.json]              关系断言回归（Golden 关系题）
  kb.py export                         导出 _out/graph.json + graph.mmd + graph-full.mmd
  kb.py stats                          规模统计
"""
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kb_check          # noqa: E402
import kb_query as Q     # noqa: E402
import onto_rules as R   # noqa: E402
from kb_core import Graph, VAULT  # noqa: E402

LEVEL_ORDER = {"violation": 0, "warn": 1}


def ensure_dir(p):
    """本机 shim 下 mkdir(exist_ok=True) 仍会抛 EEXIST，故先判断再建。"""
    p = Path(p)
    if not p.is_dir():
        p.mkdir(parents=True, exist_ok=True)
    return p


def cmd_check(g, args):
    findings = sorted(kb_check.check(g), key=lambda x: (LEVEL_ORDER.get(x[0], 2), x[1]))
    v = [f for f in findings if f[0] == "violation"]
    w = [f for f in findings if f[0] == "warn"]
    cards = len([n for n in g.nodes.values() if not n["placeholder"]])
    ph = len(g.nodes) - cards
    lines = [f"# 校验报告（ontology v{R.ONTO_VERSION}）", "",
             f"- 卡片 {cards} 张 ｜ 未建卡占位 {ph} ｜ 边 {len(g.edges)}",
             f"- **violation {len(v)}** ｜ warn {len(w)}",
             f"- 生成时间：{dt.datetime.now():%Y-%m-%d %H:%M}", ""]
    if findings:
        # 单元格里的 | 必须转义，否则说明文字里的竖线会撑破 Markdown 表格。
        esc = lambda s: str(s).replace("|", "\\|")  # noqa: E731
        lines += ["| 级别 | 卡片 | 对象 | 说明 |", "|---|---|---|---|"]
        lines += [f"| {lvl} | {esc(name)} | {esc(obj)} | {esc(msg)} |" for lvl, name, obj, msg in findings]
    else:
        lines.append("无 findings。")
    report = "\n".join(lines) + "\n"
    print(report, end="")
    (ensure_dir(VAULT / "_out") / "check.md").write_text(report, encoding="utf-8")
    return 1 if v else 0


def _mermaid_label(text):
    return (text.replace("&", "&amp;").replace('"', "&quot;")
            .replace("<", "&lt;").replace(">", "&gt;"))


def _mermaid_edge(e, nid):
    label = e["rel"] + (f" [{e['modality']}]" if e["modality"] != "universal" else "")
    if e["qualifier"]:
        label += f" ({e['qualifier']})"
    if e["note"]:
        label += f" — {e['note']}"
    label = _mermaid_label(label).replace("|", "&#124;")
    return f'  {nid[e["src"]]} -->|{label}| {nid[e["dst"]]}'


def cmd_export(g, args):
    out = ensure_dir(VAULT / "_out")
    (out / "graph.json").write_text(
        json.dumps(g.to_skeleton(), ensure_ascii=False, indent=1), encoding="utf-8")
    # 节点 ID 用稳定序号，不用 hash()：hash() 受 PYTHONHASHSEED 随机化影响，
    # 会让每次导出的 graph.mmd 全不同，既无法 diff 也无法做图漂移检测。
    nid = {n: f"n{i}" for i, n in enumerate(sorted(g.nodes))}
    lines = ["graph LR"]
    for n in sorted(g.nodes):
        v = g.nodes[n]
        if v["placeholder"]:
            continue
        label = n if v["l2"] != R.DECISION else f"{n}<br/>{v['fm'].get('status', '')}"
        label = _mermaid_label(label).replace("&lt;br/&gt;", "<br/>")
        shape = ("[/", "/]") if v["l2"] == R.DECISION else ("[", "]") if v["l2"] != "Pattern" else ("((", "))")
        lines.append(f'  {nid[n]}{shape[0]}"{label}"{shape[1]}')
    for e in g.edges:
        if e["src"].startswith("TXT:") or e["dst"].startswith("TXT:"):
            continue
        lines.append(_mermaid_edge(e, nid))
    (out / "graph.mmd").write_text("\n".join(lines) + "\n", encoding="utf-8")
    full = ["graph LR", "  %% TXT 占位是未建模目标；边是已登记声明，未必得到完整证实"]
    placeholders = []
    for n in sorted(g.nodes):
        v = g.nodes[n]
        label = n[4:] + "（未建卡）" if v["placeholder"] else n
        full.append(f'  {nid[n]}["{_mermaid_label(label)}"]')
        if v["placeholder"]:
            placeholders.append(nid[n])
    if placeholders:
        full.append("  classDef placeholder fill:#fff4e5,stroke:#b7791f,stroke-dasharray:5 5,color:#422006")
        full.append("  class " + ",".join(placeholders) + " placeholder")
    for e in g.edges:
        full.append(_mermaid_edge(e, nid))
    (out / "graph-full.mmd").write_text("\n".join(full) + "\n", encoding="utf-8")
    visible = sum(not e["src"].startswith("TXT:") and not e["dst"].startswith("TXT:") for e in g.edges)
    print(f"已导出 graph.json（节点 {len(g.nodes)} 边 {len(g.edges)}）、graph.mmd（已建卡边 {visible}）及 graph-full.mmd（含占位，边 {len(g.edges)}）")
    return 0


def cmd_stats(g, args):
    from collections import Counter
    by_rel = Counter(e["rel"] for e in g.edges)
    by_mod = Counter(e["modality"] for e in g.edges)
    cards = [n for n, v in g.nodes.items() if not v["placeholder"]]
    print(f"卡片 {len(cards)} ｜ 未建卡目标 {len(g.nodes) - len(cards)} ｜ 边 {len(g.edges)}")
    print("按关系：" + "，".join(f"{k} {v}" for k, v in by_rel.most_common()))
    print("按模态：" + "，".join(f"{k} {v}" for k, v in by_mod.most_common()))
    print(f"决策卡 {sum(1 for n in cards if g.nodes[n]['l2'] == R.DECISION)} 张")
    return 0


def cmd_test(g, args):
    path = Path(args[0]) if args else VAULT / "_kb" / "tests.json"
    cases = json.loads(path.read_text(encoding="utf-8"))
    fn = {"ask": Q.deps, "impact": lambda gg, c: Q.deps(gg, c, reverse=True),
          "constraints": Q.constraints, "lineage": Q.lineage, "chain": Q.chain}
    ok, missing_cards = 0, []
    for c in cases:
        # 卡名解析失败逐条记 FAIL，不中断整轮：曾因一条卡名写错而抛栈，
        # 后面的断言全部没跑，输出里连一行 [FAIL] 都没有 —— 回归静默失效。
        try:
            name = g.resolve(c["card"])
        except KeyError as e:
            missing_cards.append((c["q"], c["card"]))
            print(f"[FAIL] {c['q']} {c['cmd']} {c['card']} 卡名解析失败：{e.args[0]}")
            continue
        try:
            text = fn[c["cmd"]](g, name)
        except (KeyError, ValueError) as e:
            text = f"ERR {e}"
        miss = [s for s in c.get("expect", []) if s not in text]
        bad = [s for s in c.get("forbid", []) if s in text]
        status = "PASS" if not miss and not bad else "FAIL"
        ok += status == "PASS"
        print(f"[{status}] {c['q']} {c['cmd']} {c['card']}"
              + (f" 缺={miss}" if miss else "") + (f" 不应出现={bad}" if bad else ""))
    print(f"\n断言 {ok}/{len(cases)} PASS")
    if missing_cards:
        print(f"其中 {len(missing_cards)} 条因卡名不存在而失败（多为卡已改名，需同步 tests.json）："
              + "、".join(c for _, c in missing_cards))
    return 0 if ok == len(cases) else 1


def _rel(g, name, rel, reverse):
    hits = g.closure(name, rel, reverse=reverse)
    head = f"## {name} {'⇐' if reverse else '→'} {rel}"
    return "\n".join([head] + [Q._edge_line(g, d, e, reverse) for d, e in hits]) if hits else head + "\n" + Q.NONE


def _q_deps(reverse):
    """ask / impact：带第二参数时只查这一种关系。"""
    def run(g, name, rest):
        return _rel(g, name, rest[0], reverse) if rest else Q.deps(g, name, reverse=reverse)
    return run


def _q_chain(g, name, rest):
    text = Q.chain(g, name)
    (ensure_dir(VAULT / "_out" / "chains") / f"{name}.md").write_text(text, encoding="utf-8")
    return f"{text}\n—— 已写入 _out/chains/{name}.md"


# 整库命令：直接拿图
GRAPH_CMDS = {"check": cmd_check, "export": cmd_export, "stats": cmd_stats, "test": cmd_test}
# 单卡查询：先解析卡名，返回要打印的文本
CARD_CMDS = {"ask": _q_deps(False), "impact": _q_deps(True),
             "constraints": lambda g, n, _: Q.constraints(g, n),
             "lineage": lambda g, n, _: Q.lineage(g, n),
             "chain": _q_chain}


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    cmd, args = argv[0], argv[1:]
    if cmd not in GRAPH_CMDS and cmd not in CARD_CMDS:
        print(__doc__)
        return 2
    g = Graph()
    if cmd in GRAPH_CMDS:
        return GRAPH_CMDS[cmd](g, args)
    if not args:
        print(f"用法：kb.py {cmd} <卡名|id|关键字>")
        return 2
    # 卡名解析失败 / 对非决策卡调 chain 都属于用户输入错误：一行提示，不吐 Python 栈。
    try:
        print(CARD_CMDS[cmd](g, g.resolve(args[0]), args[1:]))
    except KeyError as e:
        print(f"找不到卡片：{e.args[0]}")
        return 2
    except ValueError as e:
        print(f"用法错误：{e}")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
