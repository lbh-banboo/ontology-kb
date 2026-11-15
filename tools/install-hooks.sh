#!/bin/sh
# 安装提交前守门。幂等：可反复执行。
#   bash tools/install-hooks.sh
set -eu
ROOT="$(git rev-parse --show-toplevel)"
chmod +x "$ROOT/tools/pre-commit"
git -C "$ROOT" config core.hooksPath tools
echo "✅ 已安装：core.hooksPath = tools（提交前会跑 kb.py check + kb.py test）"
echo "   验证：git commit --allow-empty -m 'verify hook'  应打印「守门通过」"
echo "   卸载：git config --unset core.hooksPath"
