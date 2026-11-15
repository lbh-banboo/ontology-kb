"""vault → 图：读取卡片 frontmatter，构造节点与正向边（ontology v1.0 §9）。

零第三方依赖。frontmatter 只支持本库约定的子集：
  key: 标量          key: ["a", "b"]（JSON 风格行内列表）
"""
import json
import re
from pathlib import Path

import onto_rules as R

VAULT = Path(__file__).resolve().parent.parent
CARD_DIRS = ("cards", "decisions")

LINK = re.compile(r"\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]")
RELATION_KEYS = R.FORWARD | set(R.INVERSE)
# 非关系字段：值里出现 [[ ]] 也不当关系
META_KEYS = {"id", "type", "obj_type", "domain", "modality", "definition", "anchors",
             "evidence_level", "valid_from", "valid_until", "owner", "status", "question",
             "decided_at", "review_at", "aliases", "tags", "occurrences", "lead_relation"}


class ParseError(ValueError):
    pass


def parse_frontmatter(text, path):
    if not text.startswith("---\n"):
        raise ParseError(f"{path}: 缺 frontmatter")
    end = text.find("\n---", 4)
    if end < 0:
        raise ParseError(f"{path}: frontmatter 未闭合")
    fm = {}
    for n, line in enumerate(text[4:end].splitlines(), 2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, val = line.partition(":")
        if not sep or not re.fullmatch(r"[A-Za-z_][\w]*", key.strip()):
            raise ParseError(f"{path}:{n}: 无法解析『{line}』")
        val = val.strip()
        if val.startswith("["):
            try:
                val = json.loads(val)
            except json.JSONDecodeError as e:
                raise ParseError(f"{path}:{n}: 列表须为 JSON 写法（双引号）：{e}") from e
            if not all(isinstance(v, str) for v in val):
                raise ParseError(f"{path}:{n}: 列表元素须为字符串")
        else:
            val = re.sub(r"\s+#.*$", "", val).strip().strip('"')
        fm[key.strip()] = val
    return fm, text[end + 4:]


def parse_value(raw):
    """'[possible]/[instance] [[X]] (限定) | 理由' → 关系及适用模态。"""
    s, mod = raw.strip(), "universal"
    for prefix, value in (("[possible]", "possible"), ("[instance]", "instance")):
        if s.startswith(prefix):
            s, mod = s[len(prefix):].strip(), value
            break
    s, _, note = s.partition(" | ")
    m = LINK.search(s)
    if m:
        target, ph = m.group(1).strip(), False
        qual = (s[:m.start()] + s[m.end():]).strip().strip("()（）").strip() or None
    else:
        q = re.fullmatch(r"(.+?)\s*[（(]([^()（）]+)[）)]", s)
        target, ph, qual = (q.group(1).strip(), True, q.group(2).strip()) if q else (s, True, None)
    return dict(target=target, placeholder=ph, modality=mod, qualifier=qual,
                note=note.strip() or None)


class Graph:
    def __init__(self, vault=VAULT):
        self.vault = Path(vault)
        self.nodes, self.edges, self.errors = {}, [], []
        self.merged = []  # 双向登记被归并的边：[(rel, src, dst, 原始声明字段)]
        self._seen = {}
        self._load()

    # ---------- 读取 ----------
    def _load(self):
        # 两遍：先登记全部卡片，再连边——否则"链接目标卡片不存在"会受文件顺序影响。
        loaded = [c for p in self._card_files() if (c := self._load_card(p))]
        for name, fm in loaded:
            for key, vals in fm.items():
                if key not in META_KEYS:
                    self._load_field(name, key, vals)

    def _card_files(self):
        return [p for d in CARD_DIRS for p in sorted((self.vault / d).rglob("*.md"))]

    def _load_card(self, p):
        """读一张卡登记为节点；解析失败 / 重名记 error 并返回 None。"""
        try:
            fm, _ = parse_frontmatter(p.read_text(encoding="utf-8"), p)
        except (ParseError, UnicodeDecodeError) as e:
            self.errors.append(("violation", p.stem, "frontmatter", str(e)))
            return None
        if p.stem in self.nodes:
            self.errors.append(("violation", p.stem, "文件名",
                                f"卡名重复：{p} 与 {self.nodes[p.stem]['path']}"))
            return None
        self.nodes[p.stem] = dict(name=p.stem, path=str(p.relative_to(self.vault)),
                                  l2=fm.get("type"), l1=fm.get("obj_type"),
                                  placeholder=False, fm=fm)
        return p.stem, fm

    def _load_field(self, src, key, vals):
        """一个非元数据字段：白名单内的关系连边；白名单外但含链接的报错（防"伪关系"）。"""
        if key not in RELATION_KEYS:
            if any(LINK.search(v) for v in (vals if isinstance(vals, list) else [vals])):
                self.errors.append(("violation", src, key, f"字段『{key}』含链接但不在关系白名单"))
            return
        if not isinstance(vals, list):
            self.errors.append(("violation", src, key, "关系字段须为列表"))
            return
        for v in vals:
            self._add_edge(key, src, parse_value(v))

    def _add_edge(self, declared, src, pv):
        tgt = pv["target"]
        if pv["placeholder"]:
            tgt = "TXT:" + tgt
            self.nodes.setdefault(tgt, dict(name=tgt, path=None, l2=None, l1=None,
                                            placeholder=True, fm={}))
        elif tgt not in self.nodes:
            self.errors.append(("violation", src, f"{declared} → [[{tgt}]]", "链接目标卡片不存在"))
            return
        rel, a, b = R.normalize(declared, src, tgt)
        if pv["modality"] == "instance":
            qualifier = pv["qualifier"] or ""
            match = re.search(r"(?<!\d)(\d{4})-(\d{2})(?!\d)", qualifier)
            if not match or not qualifier[:match.start()].strip(" ,，、；;截至自至") or not 1 <= int(match.group(2)) <= 12:
                self.errors.append(("violation", src, f"{declared} → {pv['target']}",
                                    "[instance] 关系须在括号中写对象及合法 YYYY-MM 时间范围"))
        key = (rel, a, b, pv["modality"])
        prev = self._seen.get(key)
        if prev is not None:
            # 同一关系被双方各登记一次（如 A 写 implemented_by、B 写 implements）：
            # 归一化后是同一条边，入图只留一条，避免查询输出重复。
            if declared != prev["declared"]:
                self.merged.append((rel, a, b, prev["declared"], declared))
                if not prev["qualifier"] and pv["qualifier"]:
                    prev["qualifier"] = pv["qualifier"]
                if not prev["note"] and pv["note"]:
                    prev["note"] = pv["note"]
            else:
                self.errors.append(("warn", src, f"{declared} → [[{pv['target']}]]",
                                    "同一卡内重复登记同一条边"))
            return
        e = dict(rel=rel, src=a, dst=b, declared=declared, origin=src,
                 modality=pv["modality"], qualifier=pv["qualifier"], note=pv["note"])
        self._seen[key] = e
        self.edges.append(e)

    # ---------- 访问 ----------
    def out(self, name, rel=None):
        return [e for e in self.edges if e["src"] == name and (rel is None or e["rel"] == rel)]

    def inc(self, name, rel=None):
        return [e for e in self.edges if e["dst"] == name and (rel is None or e["rel"] == rel)]

    def touching(self, name):
        """所有与本卡相关的边（不论关系写在哪张卡上）——用于"孤岛卡"判定。"""
        return [e for e in self.edges if name in (e["src"], e["dst"])]

    def resolve(self, key):
        """卡名 / id / 卡名前缀 → 卡名；找不到或有歧义抛 KeyError。"""
        if key in self.nodes:
            return key
        hits = [n for n, v in self.nodes.items() if v["fm"].get("id") == key]
        if not hits:
            hits = [n for n in self.nodes if not n.startswith("TXT:") and key.lower() in n.lower()]
        if len(hits) != 1:
            raise KeyError(f"『{key}』匹配 {len(hits)} 张卡：{hits[:8]}")
        return hits[0]

    def label(self, name):
        n = self.nodes[name]
        if n["placeholder"]:
            return f"{name[4:]}（未建卡）"
        fm, tag = n["fm"], ""
        if fm.get("modality") == "instance":
            tag = f" [instance, 自 {fm.get('valid_from') or '?'}]"
        elif fm.get("modality") == "possible":
            tag = " [possible]"
        return f"{name} `{fm.get('id', '')}`{tag}"

    def closure(self, start, rel, reverse=False, max_depth=10):
        """沿 rel 多跳（仅 §3.3 传递关系），返回 [(depth, edge)]，BFS 去重防环。"""
        depth_cap = max_depth if rel in R.TRANSITIVE else 1
        seen, frontier, out = {start}, [start], []
        for d in range(1, depth_cap + 1):
            nxt = []
            for u in frontier:
                for e in (self.inc(u, rel) if reverse else self.out(u, rel)):
                    v = e["src"] if reverse else e["dst"]
                    out.append((d, e))
                    if v not in seen:
                        seen.add(v)
                        nxt.append(v)
            frontier = nxt
            if not frontier:
                break
        return out

    def to_skeleton(self):
        """导出与 pipeline/skeleton.json 同结构的图（用 id 而非卡名），用于迁移对账。"""
        def nid(n):
            return n if n.startswith("TXT:") else self.nodes[n]["fm"].get("id", n)
        return dict(onto_version=R.ONTO_VERSION,
                    nodes=[dict(id=nid(n), name=n, l2=v["l2"], l1=v["l1"], placeholder=v["placeholder"])
                           for n, v in self.nodes.items()],
                    edges=[dict(rel=e["rel"], src=nid(e["src"]), dst=nid(e["dst"]), modality=e["modality"],
                                qualifier=e["qualifier"], declared=e["declared"], origin=nid(e["origin"]))
                           for e in self.edges])
