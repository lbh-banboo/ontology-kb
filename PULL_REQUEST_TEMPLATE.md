# 提 PR 前先过这三关

本仓库的守门是**可执行的**，不是给人看的清单。复制下面命令，三条都过再提。

```bash
python3 vault/_kb/kb.py check     # 期望 violation 0；warn 可以有，但请在 PR 里说明
python3 vault/_kb/kb.py test      # 期望全部 PASS
python3 -m unittest discover -s vault/_kb -p "test_*.py"
```

装了 hooks 的话（`sh tools/install-hooks.sh`），提交时已经自动拦过一遍。

---

## 这个 PR 做了什么

<!-- 一句话。改规范/改代码/加文档/改示例数据，分清楚。 -->

## 影响面

<!-- 改了 tbox（_schema/ontology.md）或 onto_rules.py 的话，必须回答： -->

- [ ] 我改动了关系词表或实体类型（若否，本节可删）
  - 用了哪条现有关系组合不出来？
  - 新关系的 domain / range / 传递性 / 反推规则是什么？
  - 校验器与 `tests.json` 是否同步加了断言？

- [ ] 我改动了示例卡片（`vault/cards/`、`vault/decisions/`）
  - 是否为虚构数据？（**禁止提交任何人的真实知识内容**）
  - `kb.py stats` 的数字是否同步更新到 README「当前状态」？

## 判据

<!-- 新增的规则请附一句可执行判据。写不出判据的规则，不要进来。 -->

```
（例：kb.py check 报 violation 0 → 已实测；或：注入 X 后 check 必须报 1 条 violation → 已实测翻红）
```

## 我验证过

- [ ] `kb.py check` violation 0
- [ ] `kb.py test` 全 PASS
- [ ] 单元测试全过
- [ ] 新增/修改的判据做过变异测试（能被精确打红，不是恒真式）
- [ ] 没有引入第三方依赖（本仓库零依赖是硬约束）
- [ ] 没有提交真实个人知识内容、真实凭据、本机绝对路径
