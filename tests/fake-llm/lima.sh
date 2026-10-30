#!/usr/bin/env bash
# Фиктивный LLM-апстрим в Lima VM для проверки cliproxyapi без реальных доступов: lima.sh start|stop|status
# Провайдер к cliproxyapi подключается переменной cliproxyapi_openai_compatibility в inventories/lima.
set -euo pipefail
vm="${LIMA_VM:-golem-test}"
dir="$(cd "$(dirname "$0")" && pwd)"
case "${1:?start|stop|status}" in
  start)
    limactl copy "$dir/server.py" "$vm:/tmp/fake-llm-server.py"
    limactl shell "$vm" -- sudo install -D -m 0644 -o root -g root /tmp/fake-llm-server.py /opt/fake-llm/server.py
    limactl shell "$vm" -- sudo systemd-run --unit=fake-llm --property=DynamicUser=yes --property=MemoryMax=64M \
      --property=Restart=on-failure --setenv=FAKE_LLM_FIRST_TOKEN_DELAY="${FAKE_LLM_FIRST_TOKEN_DELAY:-0}" python3 -I /opt/fake-llm/server.py
    ;;
  stop)
    limactl shell "$vm" -- sudo systemctl stop fake-llm
    limactl shell "$vm" -- sudo rm -rf /opt/fake-llm /tmp/fake-llm-server.py
    ;;
  status) limactl shell "$vm" -- systemctl is-active fake-llm ;;
esac
