#!/usr/bin/env python3
"""kb.py 查询逻辑的隔离测试：在临时 vault 里造最小样例，验证推理纪律与校验规则。

不碰真库。运行：python3 test_kb_queries.py
"""
import datetime as dt
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from kb_core import Graph  # noqa: E402
import kb_check           # noqa: E402
import kb_query as Q      # noqa: E402

FAIL = []
TODAY = dt.date(2026, 10, 6)


def ensure_dir(p):
    p = Path(p)
    if not p.is_dir():
        p.mkdir(parents=True, exist_ok=True)
    return p


def fm_text(fm):
    """dict → frontmatter 文本行（列表按 JSON 双引号写法）。"""
    out = []
    for k, v in fm.items():
        out.append(f"{k}: {json.dumps(v, ensure_ascii=False) if isinstance(v, list) else v}")
    return out


def card(dir_, name, fm, body="正文提及 [[这里只是个提及]]，不是关系。\n"):
    (ensure_dir(dir_) / f"{name}.md").write_text(
        "\n".join(["---"] + fm_text(fm) + ["---", "", body]) + "\n", encoding="utf-8")


def case(title, got, expect=(), forbid=()):
    miss = [s for s in expect if s not in got]
    bad = [s for s in forbid if s in got]
    ok = not miss and not bad
    print(f"[{'PASS' if ok else 'FAIL'}] {title}")
    if not ok:
        FAIL.append(title)
        print("       实际输出首行：" + got.strip().splitlines()[0][:120])
        if miss:
            print("       缺：" + " / ".join(miss))
        if bad:
            print("       不应出现：" + " / ".join(bad))
    return ok


def build():
    """最小样例库：Pattern → Concept → Tool 三层 + 规则约束 + 指标 + 决策。"""
    tmp = Path(tempfile.mkdtemp(prefix="kbtest-"))
    c, d = tmp / "cards", tmp / "decisions"
    base = dict(type="Concept", modality="universal", anchors=["t"],
                evidence_level="E2", owner="lee", domain="测试域")

    def kb(**kw):
        return {**base, **kw}

    card(c, "上位Pattern", dict(id="T:P", type="Pattern", modality="universal",
                                anchors=["t"], evidence_level="E2", owner="lee",
                                domain="测试域", definition="一句话定义"))
    card(c, "约束规则", kb(id="T:R", obj_type="规则", definition="规则",
                           constrains=["[[上位Pattern]]"]))
    card(c, "子概念", kb(id="T:Sub", obj_type="概念", definition="子概念",
                         is_a=["[[上位Pattern]]"]))
    card(c, "工具X", kb(id="T:X", type="Tool", obj_type="事实", definition="旧工具",
                        valid_until="2026-01-31"))
    card(c, "工具X新版", kb(id="T:X2", type="Tool", obj_type="事实", definition="新工具",
                            supersedes=["[[工具X]]"]))
    card(c, "指标M", kb(id="T:M", obj_type="指标", definition="指标"))
    # 双向登记：子概念写 implemented_by，工具X 写 implements（归一化后是同一条边）
    card(c, "子概念", kb(id="T:Sub", obj_type="概念", definition="子概念",
                         is_a=["[[上位Pattern]]"], implemented_by=["[[工具X]]"]))
    card(c, "工具X", kb(id="T:X", type="Tool", obj_type="事实", definition="旧工具",
                        valid_until="2026-01-31", implements=["[[子概念]]"]))

    card(d, "选型D1", dict(id="T:D1", type="Decision", obj_type="决策", status="accepted",
                           question="选谁？", decided_at="2026-09-01",
                           review_at="2027-01-01", owner="lee", domain="测试域",
                           chooses=["[[工具X新版]]"],
                           rejects=["[[工具X]] | 成本高 3 倍"],
                           based_on=["[[约束规则]]"],
                           constrained_by=["[[约束规则]]"]))
    # 待决形态：proposed 且尚未定选择项 —— 决策链必须不出现「✔ 选择」段，也不许判 violation。
    card(d, "选型D2待决", dict(id="T:D2", type="Decision", obj_type="决策", status="proposed",
                               question="还没定？", review_at="2027-01-01",
                               owner="lee", domain="测试域",
                               rejects=["[[工具X]] | 与已定架构冲突"]))
    return tmp, c, d


def main():
    tmp, c, d = build()
    g = Graph(tmp)

    # 纪律 1：正文 [[ ]] 只是提及，不入图、不报错
    case("纪律1 正文提及不入图", str(g.errors), forbid=["violation"],
         )
    case("纪律1 提及不会出现在任何边里",
         "\n".join(f"{e['src']}->{e['dst']}" for e in g.edges), forbid=["这里只是个提及"])

    # 纪律 2：constrains 沿 is_a 向下继承，且不反推
    case("纪律2 子概念继承上位类的约束", Q.constraints(g, "子概念"),
         expect=["受约束于 约束规则", "继承自上位类 上位Pattern"])
    case("纪律2 上位类自身不继承子类的东西", Q.constraints(g, "上位Pattern"),
         expect=["受约束于 约束规则"])

    # 纪律 3：supersedes 双向可查，带失效日期
    case("纪律3 新版 → 旧版", Q.lineage(g, "工具X新版"),
         expect=["它替代了谁", "valid_until=2026-01-31"])
    case("纪律3 旧版 → 新版", Q.lineage(g, "工具X"),
         expect=["被谁替代（新版）", "工具X新版"])

    # 纪律 4：双向登记（A 写 measured_by / B 写 measures）归一化后只留一条
    case("纪律4 双向登记归并 1 条", str(len(g.merged)), expect=["1"])
    case("纪律4 依赖查询不重复输出",
         str(Q.deps(g, "子概念").count("由…实现 工具X `")), expect=["1"])
    case("纪律4 反查也只见一次", str(Q.deps(g, "工具X", reverse=True).count("子概念")),
         expect=["1"])

    # 纪律 5：非传递关系一跳即止，不越界
    case("纪律5 constrains 不进依赖链", Q.deps(g, "约束规则"), forbid=["上位Pattern"])

    # 决策链
    g2 = Graph(tmp)
    case("决策链 结构完整", Q.chain(g2, "选型D1"),
         expect=["# 决策链 · 选型D1", "问题：选谁？", "✔ 选择", "工具X新版", "✘ 否决",
                 "成本高 3 倍", "## 依据", "受约束于", "约束规则", "来源卡片"])
    case("check 样例库 violation 为 0",
         str([f for f in kb_check.check(g2, today=TODAY) if f[0] == "violation"]), expect=["[]"])

    # 待决形态（proposed 且未定选择项）：不得伪造「选择」段，也不得因此报 violation。
    # 云端存储选型卡在 2026-10-06 拍板后由 proposed 转为 accepted，真库里已无此形态样本，
    # 故落到夹具里守住这条分支。
    case("待决决策 无「选择」段但有否决与复核日期", Q.chain(g2, "选型D2待决"),
         expect=["状态：proposed", "复核：2027-01-01", "✘ 否决", "与已定架构冲突"],
         forbid=["✔ 选择"])
    case("待决决策 不因缺 chooses 报 violation",
         str([f for f in kb_check.check(g2, today=TODAY)
              if f[0] == "violation" and f[1] == "选型D2待决"]), expect=["[]"])

    # 负例：rejects 缺理由 → violation
    card(Path(d), "坏决策", dict(id="T:D9", type="Decision", obj_type="决策",
                                 status="accepted", question="q", decided_at="2026-09-01",
                                 review_at="2027-01-01", owner="lee", domain="测试域",
                                 chooses=["[[工具X]]"], rejects=["[[工具X]]"]))
    bad = [f for f in kb_check.check(Graph(tmp), today=TODAY)
           if f[0] == "violation" and "否决理由" in f[3]]
    case("负例 rejects 缺理由 → violation", str(bad), expect=["否决理由"])

    # 负例：instance 缺 valid_from → violation
    card(Path(c), "无日期实例", {**{k: v for k, v in dict(
        type="Tool", modality="instance", anchors=["t"], evidence_level="E2",
        owner="lee", domain="测试域", obj_type="事实", definition="实例",
        id="T:I").items()}})
    v = [f for f in kb_check.check(Graph(tmp), today=TODAY)
         if f[0] == "violation" and f[2] == "valid_from"]
    case("负例 instance 缺 valid_from → violation", str(v), expect=["valid_from"])

    shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n结论：{'PASS —— 全部通过' if not FAIL else f'FAIL {len(FAIL)} 项：' + '；'.join(FAIL)}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
