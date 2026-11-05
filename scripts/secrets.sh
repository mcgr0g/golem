#!/usr/bin/env bash
# Секреты хостов (sops + age). Вызывается из mise-задач secrets:*; см. docs/operations/secrets.md.
# Расшифрованные значения в вывод не попадают.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
secrets_dir="$root/infra/ansible/secrets"
sops_cfg="$root/.sops.yaml"
# На macOS sops по умолчанию ищет ключ в ~/Library/Application Support, фиксируем путь из документации.
export SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/keys.txt}"

die() { echo "ошибка: $*" >&2; exit 1; }
need() { command -v "$1" >/dev/null || die "не найдена команда '$1' (brew install age sops)"; }
rand_hex() { openssl rand -hex "$1"; }   # hex = [0-9a-f] ⊂ [a-z0-9]

# Именованные ключи доступа к cliproxyapi: <группа>[-<суффикс>]. Значение ключа: <имя>-<hex 24>.
# cpa хранит ключи плоским списком строк; имена нужны только здесь и в cpa-keys.txt.
key_names=(home-pi home-omp home-ccs home-oc work-pi work-omp work-ccs work-oc cell nas-01 nas-02 nas-03 nas-04 nas-05)

host_file() {
  [[ "$1" =~ ^[a-z0-9][a-z0-9-]*$ ]] || die "имя хоста: [a-z0-9-], получено '$1'"
  echo "$secrets_dir/$1.sops.yml"
}

# Шифрует stdin в файл $1 по правилам .sops.yaml (имя файла определяет правило).
encrypt_to() {
  local target="$1" tmp
  tmp="$(mktemp)"
  cat >"$tmp"
  if ! sops --config "$sops_cfg" encrypt --filename-override "${target#"$root"/}" "$tmp" >"$target.new"; then
    rm -f "$target.new" "$tmp"
    die "не удалось зашифровать $target"
  fi
  rm -f "$tmp"
  mv "$target.new" "$target"
  chmod 600 "$target"
}

ensure_key() {
  if [ -f "$SOPS_AGE_KEY_FILE" ]; then
    echo "age-ключ найден: $SOPS_AGE_KEY_FILE (не перезаписывается)"
    return
  fi
  mkdir -p "$(dirname "$SOPS_AGE_KEY_FILE")"
  chmod 700 "$(dirname "$SOPS_AGE_KEY_FILE")"
  (umask 077; age-keygen -o "$SOPS_AGE_KEY_FILE" 2>&1)
  echo "создан age-ключ: $SOPS_AGE_KEY_FILE. СДЕЛАЙТЕ БЭКАП в менеджер паролей: без него секреты не расшифровать."
}

ensure_sops_cfg() {
  [ -f "$sops_cfg" ] && return
  local pub
  pub="$(age-keygen -y "$SOPS_AGE_KEY_FILE")"
  cat >"$sops_cfg" <<EOF
creation_rules:
  - path_regex: infra/ansible/secrets/.*\\.sops\\.yml\$
    age: $pub
EOF
  echo "создан $sops_cfg"
}

mgmt_hash() { # ключ со stdin -> bcrypt cost 10 (cost 14 даёт ~0,7 с на запрос, local/research/q8)
  htpasswd -niBC 10 "" | tr -d ':\n'
}

gen_host() {
  local host="$1" mgmt
  mgmt="$(rand_hex 24)"
  cat <<EOF
app_path: "$(rand_hex 10)"
ws_path: "$(rand_hex 10)"
llm_path: "$(rand_hex 10)"
vless_users:
  - id: "$(uuidgen | tr 'A-Z' 'a-z')"
    email: "owner@$host"
cliproxyapi_named_keys:
$(for n in "${key_names[@]}"; do printf '  %s: "%s-%s"\n' "$n" "$n" "$(rand_hex 24)"; done)
cliproxyapi_management_key: "$mgmt"
cliproxyapi_management_key_hash: '$(printf '%s' "$mgmt" | mgmt_hash)'
EOF
}

cmd_init() {
  need age; need sops; need openssl; need htpasswd
  local host="${1:?использование: secrets.sh init <host>}" f common
  f="$(host_file "$host")"
  common="$(host_file common)"
  ensure_key
  ensure_sops_cfg
  mkdir -p "$secrets_dir"
  chmod 700 "$secrets_dir"
  if [ -e "$common" ]; then
    echo "уже есть: $common"
  else
    encrypt_to "$common" <<'EOF'
duckdns_token: ""
telegram_bot_token: ""
telegram_chat_id: ""
EOF
    echo "создан $common (заполните: mise run secrets:edit common)"
  fi
  if [ -e "$f" ]; then
    echo "уже есть: $f (для замены значений: secrets:rotate $host)"
  else
    gen_host "$host" | encrypt_to "$f"
    echo "создан $f"
  fi
}

cmd_edit() {
  need sops
  local f
  f="$(host_file "${1:?использование: secrets.sh edit <host|common>}")"
  [ -f "$f" ] || die "нет файла $f (secrets:init <host>)"
  sops edit "$f"
}

# Значения передаются в sops через stdin (не попадают в список процессов).
# sops set не принимает JSON-массивы целиком, поэтому правим скалярные элементы: структура создаётся в init.
set_value() { # файл, путь sops, значение (строка)
  printf '"%s"' "$3" | sops set --value-stdin "$1" "$2"
}
cmd_rotate() {
  need sops; need openssl; need htpasswd
  local host="${1:?использование: secrets.sh rotate <host> <uuid|paths|mgmt|all>}"
  local what="${2:?укажите что ротировать: uuid|paths|mgmt|all}" f mgmt
  f="$(host_file "$host")"
  [ -f "$f" ] || die "нет файла $f"
  case "$what" in uuid|paths|mgmt|all) ;; *) die "неизвестная цель '$what'" ;; esac
  if [[ "$what" == uuid || "$what" == all ]]; then
    set_value "$f" '["vless_users"][0]["id"]' "$(uuidgen | tr 'A-Z' 'a-z')"
    echo "ротирован: vless_users[0].id"
  fi
  if [[ "$what" == paths || "$what" == all ]]; then
    for k in app_path ws_path llm_path; do
      set_value "$f" "[\"$k\"]" "$(rand_hex 10)"
    done
    echo "ротированы: app_path ws_path llm_path"
  fi
  if [[ "$what" == mgmt || "$what" == all ]]; then
    mgmt="$(rand_hex 24)"
    set_value "$f" '["cliproxyapi_management_key"]' "$mgmt"
    set_value "$f" '["cliproxyapi_management_key_hash"]' "$(printf '%s' "$mgmt" | mgmt_hash)"
    echo "ротирован: ключ management CPA"
  fi
  echo "дальше: ansible:site <env> --tags caddy,xray, затем перегенерация clients/generated/"
}

case "${1:-}" in
  init) shift; cmd_init "$@" ;;
  edit) shift; cmd_edit "$@" ;;
  rotate) shift; cmd_rotate "$@" ;;
  *) die "использование: secrets.sh init|edit|rotate ..." ;;
esac
