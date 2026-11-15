# 变更记录

格式参照 Keep a Changelog；版本号参照 SemVer。
本仓库的「版本」指**规范与工具的兼容性**，不指卡片内容数量。

## [0.1.0] — 2026-11-15

首个公开版本。内容为方法与工具，**不含任何人的真实知识卡片**。

### 新增

- `vault/_schema/ontology.md` v1.0（public）：TBox 规范
  - 5 类实体（Concept / Method / Tool / Scenario / Pattern）
  - 15 条关系（结构 7 + 治理与时态 5 + 决策 3）
  - 关系语义属性表（domain/range、传递性、反推、模态、前置条件）
  - 模态三分（universal / possible / instance）与写法
  - 决策层（生命周期 + chooses / rejects / based_on）
- `vault/_kb/` 零依赖 CLI
  - `kb.py check` 写入前校验
  - `kb.py ask / impact / constraints / lineage / chain` 查询
  - `kb.py test` 关系回归题集
  - `kb.py export / stats` 导出与统计
- `tools/pre-commit` 提交前守门（三道拦截）+ `install-hooks.sh`
- `.github/workflows/guard.yml` CI 守门（9 道断言：violation／关系回归／unittest／关系计数／敏感串／
  workflow 自检／示例库规模／失败模式条数／URL 占位符）。actions pin 到 commit SHA，
  `permissions: contents: read`，`persist-credentials: false`
- `docs/` 11 篇方法与步骤文档，含 17 条失败模式与 12 步 playbook
- `vault/cards/`、`vault/decisions/` 虚构示例数据集（11 张卡，咖啡冲煮域），用于验证规范与工具
- `tests.json` 演示规模回归题集（10 题，含 1 条负样本）

### 修正（相对内部 v0.3 规范）

- 统一关系计数：标题「11 个」→ 与表格、代码一致的 12（结构 7 + 治理 5），决策关系 3 另计，合计 15
- `anchors` 口径：从「必须是稳定 media_id」改为「可独立定位即可」，
  因原口径在真实使用中全库无一张卡合规，而校验器只查非空——规范与判据不一致（F4）
- `owner` 字段：示例中统一为角色而非私人称呼
- 补齐 §7「落地清单」，如实列出尚未实现的口径

### 修正（首轮 CI 跑出来的）

首推后 CI 红了，红在自带守门脚本上，两条都是判据自身的缺陷，已固化为 F16 / F17：

- F16：敏感串扫描的模式文本写在自己要扫的 workflow 里，`git grep` 把它当成命中物，
  自指恒红。修法：排除本文件 + 补一条不依赖字面量的结构断言（不许出现 `secrets.` 与凭据型 `env:`）
- F17：模式里的 `\s` 是 GNU 扩展，macOS 的 BSD 引擎不认，本机「已验证通过」形同虚设。
  修法：一律改用 POSIX 字符类 `[[:space:]]`
- 另补一道断言，把失败模式条数钉在 4 处口径上（F1 的复发点）

### 修正（第二轮：投放前审核跑出来的）

- `CITATION.cff` 与 README 的 clone 命令里仍保留着未替换的用户名占位（发布后是 404）
  —— 脱敏把账号名换成占位符，忘了这两处是给人点的。已换成真实地址
  （此处刻意不复述那个占位写法：写出来就正好是第 9 道断言的靶子）
- 补第 9 道断言「URL 占位符残留」，与 preflight G10 互补（G10 管带尖括号的模板词，
  本步管已无尖括号但仍是占位的用户名）
- 敏感串黑名单移除 `lbh-banboo`：它是本仓库的公开托管账号，已写在 URL 里，
  强制占位会让 clone 命令不可用；私有账号与私有仓库名仍保留在名单内

### 已知限制

- 评测门槛 **PENDING**：示例库未建 100 题级冻结题集，四项门槛无实测数字
- `anchors` 仍无数值格式判据，`possible` 模态尚无「不得作为答案直引」的机器判据
- 守门为全量检查，未做增量优化（几千张卡时会变慢，见 docs/05 §5.7）
