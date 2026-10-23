#!/usr/bin/env bash
# Собирает config.yaml (содержит секреты, 0600, в .gitignore): render.sh <host>
set -euo pipefail
host="${1:?укажите хост инвентори: render.sh <host>}"
dir="$(cd "$(dirname "$0")" && pwd)"
node="$dir/../../clients/generated/$host/mihomo-node.yaml"
[ -f "$node" ] || { echo "нет $node: сначала mise run ansible:site <env>" >&2; exit 1; }
name="$(awk -F'"' '/- name:/{print $2; exit}' "$node")"
umask 077
{
  cat "$dir/base.yaml"
  cat "$node"
  printf 'rules:\n  - MATCH,%s\n' "$name"
} > "$dir/config.yaml"
echo "config.yaml собран для $host (узел $name)"
