"""守门与推理纪律回归：仅 Python 标准库。运行：python3 test_governance.py

与 test_kb_queries.py 的分工：那个测查询函数的输出细节，这个测「规范里写了但代码是否真拦得住」。
每条断言都必须能因为**某个具体违规**而失败——测不出失败的断言不算断言。
"""
import datetime as dt
import tempfile
import unittest
from pathlib import Path

import kb_check
import kb_query
from kb_core import Graph, parse_value

TODAY = dt.date(2026, 11, 15)


def tmp_vault(cards=(), decisions=()):
    """建一个临时 vault：cards/decisions 目录 + 若干卡文本，返回 (ctx, vault)。"""
    tmp = tempfile.TemporaryDirectory()
    vault = Path(tmp.name)
    (vault / "cards").mkdir()
    (vault / "decisions").mkdir()
    for name, text in cards:
        (vault / "cards" / f"{name}.md").write_text(text, encoding="utf-8")
    for name, text in decisions:
        (vault / "decisions" / f"{name}.md").write_text(text, encoding="utf-8")
    tmp.cleanup()


class GovernanceTests(unittest.TestCase):
    # ---------- 模态 ----------
    def test_instance_value_keeps_target_and_scope(self):
        edge = parse_value("[instance] 示例目标 (某系统，截至 2026-09)")
        self.assertEqual((edge["target"], edge["modality"], edge["qualifier"]),
                         ("示例目标", "instance", "某系统，截至 2026-09"))

    def test_instance_without_time_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            (vault / "cards").mkdir()
            (vault / "decisions").mkdir()
            (vault / "cards" / "案例.md").write_text(
                "---\nid: x\ntype: Concept\nobj_type: 事实\nmodality: instance\n"
                "applies_to: [\"[instance] 示例 (只有对象)\"]\n---\n", encoding="utf-8")
            graph = Graph(vault)
            self.assertTrue(any("YYYY-MM" in e[3] for e in graph.errors),
                            "instance 边缺 YYYY-MM 时间范围必须报错，否则等于允许无时点的事实")

    def test_instance_scope_is_rendered(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            (vault / "cards").mkdir()
            (vault / "decisions").mkdir()
            (vault / "cards" / "场景.md").write_text(
                "---\nid: s\ntype: Scenario\nobj_type: 流程\nmodality: universal\n"
                "definition: d\nanchors: [\"x\"]\nevidence_level: C\nowner: o\n---\n",
                encoding="utf-8")
            (vault / "cards" / "观察.md").write_text(
                "---\nid: o\ntype: Concept\nobj_type: 事实\nmodality: instance\n"
                "definition: d\nanchors: [\"x\"]\nevidence_level: C\nowner: o\nvalid_from: 2026-09-01\n"
                "applies_to: [\"[instance] [[场景]] (某系统，截至 2026-09)\"]\n---\n",
                encoding="utf-8")
            shown = kb_query.constraints(Graph(vault), "观察")
            self.assertIn("[instance]", shown, "实例边必须在输出里带上模态标记")
            self.assertIn("截至 2026-09", shown, "限定范围必须可见，否则读者会把实例当通用结论")

    # ---------- 指标口径 ----------
    def test_metric_requires_four_fields(self):
        graph = Graph()
        fm = graph.nodes["萃取率"]["fm"]
        required = ("metric_numerator", "metric_denominator", "metric_source", "metric_window")
        self.assertTrue(all(fm.get(k) for k in required), "示例指标卡应写全四口径")
        self.assertFalse(any("指标口径字段缺失" in f[3] for f in kb_check.check(graph, TODAY)))
        for k in required:
            with self.subTest(dropped=k):
                backup = fm.pop(k)
                try:
                    self.assertTrue(
                        any("指标口径字段缺失" in f[3] for f in kb_check.check(graph, TODAY)),
                        f"删掉 {k} 后必须报 warn，否则该字段等于没被校验")
                finally:
                    fm[k] = backup

    # ---------- 正文提及 vs typed 关系 ----------
    def test_body_link_is_not_a_relation(self):
        graph = Graph()
        out = graph.out("2026-03 首次手冲记录")
        self.assertEqual([e["rel"] for e in out], ["evidence_for"],
                         "正文里的 [[注水手法]] 不得变成关系；只有 frontmatter 字段进图")
        self.assertIn("（库内无此关系登记）", kb_query.deps(graph, "2026-03 首次手冲记录"))

    # ---------- Pattern 免填 obj_type ----------
    def test_pattern_exempt_from_obj_type(self):
        graph = Graph()
        self.assertIsNone(graph.nodes["P1 先定不变量"]["fm"].get("obj_type"))
        v = [f for f in kb_check.check(graph, TODAY)
             if f[0] == "violation" and f[1] == "P1 先定不变量"]
        self.assertFalse(v, f"Pattern 不应因缺 obj_type 被判 violation，实得 {v}")

    # ---------- 决策生命周期 ----------
    def test_superseded_decision_needs_valid_until(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            (vault / "cards").mkdir()
            (vault / "decisions").mkdir()
            base = ("---\nid: {i}\ntype: Decision\nobj_type: 决策\nstatus: {s}\n"
                    "question: q\nreview_at: 2027-01-01\nowner: o\n{extra}---\n")
            (vault / "decisions" / "旧.md").write_text(
                base.format(i="d1", s="superseded", extra="decided_at: 2026-01-01\n"
                            "chooses: [\"新\"]\n"), encoding="utf-8")
            (vault / "decisions" / "新.md").write_text(
                base.format(i="d2", s="accepted", extra="decided_at: 2026-02-01\n"
                            "chooses: [\"旧\"]\nsupersedes: [\"[[旧]]\"]\n"), encoding="utf-8")
            findings = kb_check.check(Graph(vault), TODAY)
            self.assertTrue(any("valid_until" in f[2] for f in findings),
                            "被替代方未写 valid_until 必须报 violation")


if __name__ == "__main__":
    unittest.main()
