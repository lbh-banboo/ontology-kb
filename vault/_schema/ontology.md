# 本体受控词表（TBox）

版本：v1.0（public）｜ 状态：**本仓库唯一真相源**
适用：`vault/` 下的示例库；裁剪后可用于任意领域——改 §2 的类型、§3 的关系、§4 的域取值即可。

> 本文件只定义**合法类型与合法关系**。写入前必须检查三件事：实体类型在 §2 内、关系类型在 §3 内、必填字段在 §5 内齐全。
> 它不定义任何领域知识——知识写在 `vault/cards/` 里。

## 0. 用途与纪律

三条纪律，比任何字段都重要：

1. **先形成最小可用分类与核心实体，随场景扩展本体**。不在业务应用出现之前建设庞大而抽象的全公司本体。
2. **不在词表内的类型和关系一律不许入库**，需要时先走「申请扩表」流程（见 `CONTRIBUTING.md`），不许自造。
3. **文档只是载体，不是最终知识形态**。一条知识写进卡片后，它的价值来自关系，不来自篇幅。

三层分工：

| 层 | 回答什么 | 载体 |
|---|---|---|
| 知识图谱（A-Box） | 有哪些实例、实例之间的事实是什么 | 卡片 frontmatter + 正文 |
| 本体（T-Box） | 允许有哪些类型和关系 | 本文件 |
| 业务规则（决策层） | 在约束下怎么选 | 决策卡 |

## 1. L1 知识对象层（形态）

回答「这条知识是什么形态」。

| 类型 | 判据 |
|---|---|
| 事实 Fact | 发生了什么、依据是什么 |
| 规则 Rule | 必须/禁止怎么做，含红线与例外 |
| 流程 Process | 从输入到输出的步骤序列 |
| 决策 Decision | 在若干选项间的选择及其理由 |
| 案例 Case | 具体场景下的真实过程与结果 |
| 指标 Metric | 可量化的度量及口径 |
| 风险 Risk | 可能出错之处及后果 |
| 行动 Action | 待执行或已执行的具体动作 |

## 2. L2 本体骨架层（实体类型）

回答「这是什么东西」。

| 类型 | 定义 | 判据 |
|---|---|---|
| Concept 概念 | 不可再分或被多方共同引用的认知单元 | 多处被 depends_on 指向 |
| Method 方法 | 可复用的做法与技术路径 | 能回答「怎么做」 |
| Tool 工具·平台 | 承载方法的具体系统 | 有名字、能装能调 |
| Scenario 场景 | 业务问题或任务 | 能回答「为谁解决什么」 |
| Pattern 模式 | 跨领域复现的同构结构 | 在不相邻的 ≥3 个领域独立出现 |

类别层级（is_a 树根）：`Thing → {Concept, Method, Tool, Scenario, Pattern}`。

> `Rule` / `Risk` **不是** L2 类型，而是 L1 形态。ID 中允许 `rule` / `risk` 段仅作可读性前缀，
> 其 L2 类型必须落到五类之一（默认 Rule→Concept，Risk→Concept）。
> 这一条是最常被写错的：把「规则」当实体类型，`constrains` 的 domain 校验会立刻失真。

## 3. 关系类型（结构类 7 + 治理与时态类 5 = 12；§8 决策关系另计 3，合计 15）

### 3.1 结构类（7）

| 关系 | 含义 | 反向 |
|---|---|---|
| is_a | 上位/实例化 | has_subtype |
| part_of | 组成 | has_part |
| depends_on | 依赖（逻辑或技术前置） | required_by |
| implemented_by | 由…实现 | implements |
| applies_to | 适用于（指向 Scenario） | applicable_rule |
| measured_by | 由…度量（指向指标） | measures |
| produces | 产出 | produced_by |

### 3.2 治理与时态类（5）

| 关系 | 含义 | 使用要求 |
|---|---|---|
| supersedes | 替代（新取代旧） | 被替代方必须写 valid_until |
| conflicts_with | 冲突 | 必须写裁定结论与理由 |
| evidence_for / evidenced_by | 证据支撑 | 相互成对登记 |
| constrains | 硬约束/红线 | 必须可验收（0/1 判定） |
| calibrated_by | 阈值由…标定 | 指向评测集或人工标定集 |

> 计数口径以前写错过：标题写「11 个」，而表格是 7+5=12，代码里的白名单是 12，
> 决策层又加了 3 个却没改标题。**任何一处数字与代码不一致，都按 bug 处理**——
> 外部读者按标题建卡会漏 `calibrated_by`，按标题写校验器会漏 4 类关系。
> 现在标题、表格、`vault/_kb/onto_rules.py` 的 `FORWARD` 三处必须相等，且由 CI 断言。

### 3.3 关系语义属性表

| 关系 | domain → range | 传递 | 对称 | 反推是否成立 | 模态 | 前置条件 |
|---|---|---|---|---|---|---|
| is_a | 任意 → 同类或上位类 | 是 | 否 | 否（子类成立≠父类成立） | 通用 | 无环 |
| part_of | 任意 → 任意 | 是 | 否 | 否 | 通用 | 无环 |
| depends_on | 任意 → Concept/Method/Tool | 是（用于影响分析） | 否 | 否 | 通用 | 无环；被依赖方须已存在 |
| implemented_by | Concept/Method → Tool/Method | 否 | 否 | 否（工具实现 A≠工具只做 A） | 通用 | — |
| applies_to | 任意 → Scenario | 否 | 否 | 否 | 通用 | 目标须是 Scenario |
| measured_by | 任意 → 指标(obj_type=指标) | 否 | 否 | 否 | 通用 | 指标须写四口径，缺项报 warn |
| produces | Method/Tool → 任意 | 否 | 否 | 否 | 通用 | — |
| supersedes | X → 同类 X | 是 | 否 | — | 时态 | 被替代方 valid_until 必填 |
| conflicts_with | 任意 ↔ 任意 | 否 | 是 | — | 通用 | 必须附裁定 |
| evidence_for | Case/Fact → 任意 | 否 | 否 | 否（证据支持≠充分证明） | 实例 | 须标 evidence_level |
| constrains | Rule/Pattern → 任意 | 沿 is_a 向下继承 | 否 | 否 | 通用 | 须可 0/1 判定 |
| calibrated_by | 阈值条目 → 评测集/标定集 | 否 | 否 | 否 | 实例 | 标定集须有版本号 |

**推理纪律（写死在代码里，不靠自觉）：**

1. 只有「传递=是」的关系才允许做多跳推理；其他关系一跳即止。`kb_query.py` 的 `TRANSITIVE` 是唯一开关。
2. 「反推是否成立=否」的关系，禁止从目标反推源头。典型错误：由「糖尿病表现为多饮」推出「多饮的人有糖尿病」。
3. `constrains` 沿 `is_a` 向下继承：父类受约束 ⇒ 子类受约束；反之不成立。
4. 反向查询只列出「谁指向它」这一事实，不推断因果。

### 3.4 模态区分

| 模态 | 含义 | 示例 | 写法 |
|---|---|---|---|
| 通用 universal | 对该类所有实例成立的规则 | Skill 必须有 fallbacks | 写在 T-Box 或 Concept/Rule 条目 |
| 可能 possible | 可能发生，不等于已发生 | 换 embedding 模型可能导致语义错位 | 关系值前标 `[possible]` |
| 实例 instance | 某个具体对象上已发生的事实 | 某系统截至 2026-09 的能力缺口 | 卡片须 `valid_from`；关系值写 `[instance] [[目标]] (对象，截至 YYYY-MM)` |

**禁止**：把 possible 当 instance 回答；把 instance 当 universal 推广。
这两条是本库最容易产生的幻觉来源——因为两者在中文里都长得像「事实」。

## 4. 条目 ID 命名

格式：`KB:<域>.<L2类型或形态前缀>.<名称>`

`<域>` 由使用者自定，建议 2–8 个小写字母，一域一值。本仓库示例用 `coffee`：

```
KB:coffee.concept.ExtractionYield
KB:coffee.method.PourOver
KB:coffee.metric.TDS
KB:dec.20260110.GrinderChoice      # 决策卡用 dec.<YYYYMMDD>.<名称>
```

ID 一旦对外引用就不再改名——它是外部系统唯一能稳定握住的把手。

## 5. 必填字段（缺一不予入库）

| 字段 | 说明 |
|---|---|
| id | 见 §4 |
| name | 名称（= 文件名，见 §9） |
| type | L2 五类之一；决策卡固定 `Decision` |
| obj_type | L1 八类之一（Pattern 免填） |
| domain | 所属域 |
| definition | 一句话定义，不含模糊词（「较好」「适当」这类词不算定义） |
| modality | universal / possible / instance |
| relations | 至少一条 typed 关系，格式 `关系 → 目标` |
| anchors | 至少一个**可独立定位**的来源标识：文件名+章节、URL、标准号、页码均可 |
| evidence_level | A 官方/监管/标准；B 企业官方体系与成熟方法；C 从业者公开内容 |
| valid_from / valid_until | 可失效内容必填；未填视为长期有效但需复核 |
| owner | 责任人（写角色或账号，不写私人称呼） |

> **关于 `anchors` 的历史教训**：早期规范要求「稳定 media_id」，但整库 anchors
> 全是笔记名/章节名，0 个符合；而校验器只查「字段非空」，于是 `violation 0` 掩盖了
> 「规范自己宣布自己未生效」。现在的口径是**可独立定位即可**，且不再假装有 media_id。
> 教训：**必填 ≠ 已校验格式**。凡是「必填」字段，必须在 `kb_check.py` 里有对应判据，否则就删掉这条必填。

## 6. 写入前自检（6 条）

1. 类型与关系是否都在词表内（不在则先申请扩表，不得自造）
2. 是否已有同义条目（异名同责归并、同名不同责拆分）
3. 会失效的内容是否填了 `valid_until` 与校验方式
4. 约束类条目是否可验收（能判 0/1）
5. 阈值类条目是否标了 `calibrated_by`
6. 关系是否满足 §3.3 的 domain/range 与前置条件；`modality` 是否填写

## 7. 落地清单（本公开版尚未做完的部分，如实列出）

- [ ] `anchors` 格式判据尚未加进 `kb_check.py`（当前只查非空）
- [ ] `possible` 模态尚无「不得作为答案直接引用」的机器判据
- [ ] 示例库只有 11 张卡，未覆盖「同义条目归并」的冲突场景
- [ ] 评测题集为演示规模，**未达标**，见 `docs/06-evaluation.md`

> 这一节刻意保留空项。把「没做完」写进规范，比让读者从别处发现它没做完要好。

## 8. 决策层（Decision）

Decision 是独立的第六类节点（不是 L2 五类之一，也不只是 L1「决策」形态）。
理由：决策有生命周期（proposed → accepted → superseded / rejected），而知识条目没有；混在一起会让 is_a / constrains 继承规则失真。

### 8.1 Decision 必填字段

| 字段 | 说明 |
|---|---|
| id | `KB:dec.<YYYYMMDD>.<名称>` |
| type | 固定 `Decision` |
| obj_type | 固定 `决策` |
| status | proposed / accepted / superseded / rejected |
| question | 要解决的问题，一句话 |
| chooses | 至少 1 个（status=proposed 时可空，但须有 options 正文） |
| decided_at | 决策日期（proposed 可空） |
| review_at | 复核日期（到期由 check 报 warn） |
| owner | 责任人 |

### 8.2 决策关系（3）

| 关系 | domain → range | 传递 | 要求 |
|---|---|---|---|
| chooses | Decision → 任意 | 否 | — |
| rejects | Decision → 任意 | 否 | 必须带理由（`"[[X]] | 理由"`，缺理由判 violation） |
| based_on | Decision → 任意 | 否 | 依据的规则/事实/证据 |
| constrained_by | Decision → Rule/Pattern | 沿 is_a 继承 | 存储时翻转为 `constrains`（源须 L1 规则或 Pattern） |
| supersedes | Decision → Decision | 是 | 被替代决策 status=superseded 且须写 valid_until |

> `chooses` / `rejects` / `based_on` 合计 3 个是**决策专属**关系，不计入 §3 的 12 个。
> 标题口径：§3 = 12，§8 = 3，全库合计 15。

## 9. 卡片存储约定

- 一张卡 = 一个 `.md` 文件，**文件名 = 卡片显示名**；`[[文件名]]` 即引用。改名 = 断链，务必全局替换。
- **只有 frontmatter 中关系字段里的链接才是 typed 关系**；正文 `[[ ]]` 只是提及，不参与推理。
- 关系字段可写正向名或反向名（如 `has_part`），入图时统一翻转为正向。
- 关系值写法：

| 场景 | 写法 |
|---|---|
| 已建卡 | `"[[卡名]]"` |
| 未建卡 | 纯文本（成为占位节点，check 报 warn，**允许存在**） |
| 可能发生 | `"[possible] [[卡名]]"` |
| 实例事实 | `"[instance] [[卡名]] (对象，截至 YYYY-MM)"` |
| 带说明 | `"[[卡名]] (说明)"` |
| 带理由（rejects / conflicts_with） | `"[[卡名]] | 理由"` |

- 指标卡被 `measured_by` 引用时，须明确四口径：`metric_numerator`（分子或计数规则）、`metric_denominator`（分母）、`metric_source`（取证来源）、`metric_window`（统计样本/时间窗）。缺项报 warn，**不许用空卡消警**。
- `_out/` 全部可由 `kb.py` 重建，可随时删除，不纳入版本管理。
