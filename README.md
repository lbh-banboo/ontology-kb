# ontology-kb · 用本体管住个人知识库的方法与工具

**一个不靠向量检索、不靠 LLM 猜关系的个人知识库方案。**
关系写进 frontmatter 成为结构化数据，于是它可以被确定性查询、被回归测试、被提交前拦截。

**本仓库只提供方法与工具，不含任何人的真实知识内容。** 卡片目录里是一套虚构的示例数据集（手冲咖啡域），用于证明规范与工具能跑通。

## 快速开始

无需安装，零第三方依赖，Python 3.9+ 即可跑：

```bash
git clone https://github.com/OWNER/ontology-kb && cd ontology-kb

python3 vault/_kb/kb.py check     # 校验：期望 violation 0
python3 vault/_kb/kb.py test      # 回归：期望 10/10 PASS
python3 vault/_kb/kb.py stats     # 规模：11 卡 / 1 占位 / 19 边
python3 vault/_kb/kb.py ask 注水手法   # 查询：它依赖什么
```

想把它变成自己的库：`docs/10-playbook.md` 的 12 步，每步都有验收判据。

---

## 它解决什么问题

笔记越攒越多之后，真正让人痛苦的通常不是「找不到原文」，而是这几类问题：

- 「A 换了，哪些东西要跟着改？」
- 「这个结论是哪一版定下来的，之前那版为什么被否？」
- 「这条规则是从哪来的，有没有依据？」
- 「这句话是通用结论，还是某个系统在某个时间点的情况？」

全文搜索和向量检索都答不了这些——它们返回「看起来像的段落」，
而上面每一问都需要**显式的、有方向的、可校验的关系**。

本仓库的做法：**把关系写下来，当成数据管。**

| | 常见做法 | 本仓库 |
|---|---|---|
| 关系存在哪 | 隐式（向量邻近性 / 正文超链接） | frontmatter 关系字段 |
| 怎么得到答案 | 召回 + 生成 | 图上遍历，只输出已登记的边 |
| 怎么验对错 | 看结果像不像 | 断言 `ask A depends_on` 必须含 B |
| 同一问题问两次 | 可能不同 | 一定相同 |
| 出错能否定位 | 不能 | 能，指到具体卡的具体字段 |

## 三条设计原则

1. **不做自动关系抽取。** 猜出来的关系无法判定对错，无法判定就无法回归。理由见 [docs/01](docs/01-why-not-vector-first.md)。
2. **不做大而全的本体。** 只建 5 类实体、15 条关系。够用一年，多建是负债。
3. **不宣称未验证的准确率。** 本仓库评测状态是 `PENDING`，下面如实列出。

## 目录结构

```
.
├── vault/                    ← 一个 vault = 一个知识库
│   ├── _schema/ontology.md   ← TBox：类型与关系的唯一定义
│   ├── _kb/                  ← 工具链（零依赖）
│   │   ├── kb.py             ← CLI：check / ask / impact / constraints / lineage / chain / test
│   │   ├── kb_core.py        ← frontmatter → 图
│   │   ├── kb_check.py       ← 校验规则
│   │   ├── kb_query.py       ← 查询（推理纪律写死在代码里）
│   │   ├── onto_rules.py     ← ontology.md 的机器可执行版本
│   │   └── tests.json        ← 关系回归题集（演示规模 10 题）
│   ├── _templates/           ← 卡片模板
│   ├── cards/                ← 知识卡（示例：11 张，虚构）
│   └── decisions/            ← 决策卡（示例：2 张，虚构）
├── tools/
│   ├── pre-commit            ← 提交前守门（三道拦截）
│   └── install-hooks.sh
└── docs/                     ← 方法与步骤（本仓库的主体）
```

## 文档（方法与步骤）

| 篇 | 讲什么 |
|---|---|
| [00 导航](docs/00-index.md) | 按处境选读 |
| [01 为什么不先上向量检索](docs/01-why-not-vector-first.md) | 检索问题 vs 数据问题 |
| [02 划域与最小本体](docs/02-scope-and-ontology.md) | 5 类实体、15 条关系的选型口诀 |
| [03 卡片规范](docs/03-card-spec.md) | 每字段的坑 + 六种关系写法 |
| [04 正文提及 vs 关系](docs/04-body-vs-relation.md) | 最大的混淆源 |
| [05 守门放在提交前](docs/05-guardrail.md) | 三道拦截的阈值设计 |
| [06 生命周期](docs/06-lifecycle.md) | 过期、替代链、复核 |
| [07 评测](docs/07-evaluation.md) | 冻结题集、四项门槛、拒答率 |
| [08 同步与唯一写入点](docs/08-sync-single-writer.md) | 云盘镜像 + Git 单向出口 |
| [09 17 条失败模式](docs/09-failure-modes.md) | 全是踩过的 |
| [10 Playbook](docs/10-playbook.md) | **12 步，每步有验收判据** |

如果只想看一份文档：读 [docs/10-playbook.md](docs/10-playbook.md)。

## 核心概念（30 秒版）

```markdown
---
id: KB:coffee.method.Pour
type: Method            # 五类之一：Concept / Method / Tool / Scenario / Pattern
obj_type: 流程           # 八类形态之一
domain: 咖啡冲煮域
modality: universal     # universal / possible / instance
definition: 分三段注水并各留一次排气间隙的做法
part_of: ["[[手冲咖啡]]"]          # ← typed 关系，进图
implemented_by: ["[[V60 滤杯]]"]   # ← typed 关系，进图
anchors: ["示例数据：虚构"]
evidence_level: C
owner: kb-maintainers
---

正文里提到 [[金杯准则]] 只是提及，不进图。
```

查询：

```bash
python3 vault/_kb/kb.py ask 注水手法        # 它依赖什么
python3 vault/_kb/kb.py impact 手冲咖啡      # 改它会影响谁
python3 vault/_kb/kb.py lineage D-20260110-新手训练路径   # 谁替代了谁
python3 vault/_kb/kb.py chain D-20260401-新手训练路径改版  # 完整决策链
```

## 明确不包含什么

| 不包含 | 原因 |
|---|---|
| 任何个人的真实知识卡片 | 本仓库只开源**方法与工具**；示例数据为虚构，与作者的真实知识库无关 |
| 内部文档、内部系统名、内部链接 | 与读者无关，且不可移植 |
| 第三方项目源码 | 需要时给来源与许可，不复制 |
| 完整量级的评测题集 | 只给演示规模的 10 题与建题方法 |

## 当前状态

| 项 | 状态 |
|---|---|
| `kb.py check` | ✅ violation 0（示例库） |
| `kb.py test` | ✅ 10/10 PASS（示例规模） |
| 单元测试 | ✅ 2 个测试文件全过 |
| 评测门槛 | ⚠️ **PENDING** — 示例库未建 100 题级题集，四项门槛无实测数字 |
| 本体完备性 | ⚠️ 见 [ontology.md §7 落地清单](vault/_schema/ontology.md) 的未完成项 |

> 第三、四行是刻意保留的。把没做完的写在自己的 README 里，
> 比让读者从别处发现要好——这也是 [docs/07](docs/07-evaluation.md) 的立场。

## 贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md)。最需要的一种贡献：**报告一个失败模式，并附上可执行的判据。**

## 许可

- 代码（`tools/`、`vault/_kb/`、CI 配置）：[Apache-2.0](LICENSE)
- 文档与卡片内容（`docs/`、`vault/cards/`、`vault/decisions/`、`vault/_schema/`）：[CC BY 4.0](LICENSE-CONTENT.md)

引用方式见 [CITATION.cff](CITATION.cff)。
