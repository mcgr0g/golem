#!/usr/bin/env bash
# Сборка артефактов на Mac (на VPS не собираем, AGENTS.md). Документация: docs/operations/build-artifacts.md
# Использование: scripts/build-artifacts.sh [caddy|web|relay|all ...]   (по умолчанию all)
# Переменные: TARGET_ARCH=amd64|arm64 (amd64), CADDY_VERSION, XCADDY_VERSION, OMP_TAG, OMP_SRC, BUN_RETRIES.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
build="$root/build"
arch="${TARGET_ARCH:-amd64}"
caddy_version="${CADDY_VERSION:-v2.11.7}"
xcaddy_version="${XCADDY_VERSION:-latest}"
bun_retries="${BUN_RETRIES:-3}"
omp_repo="https://github.com/can1357/oh-my-pi"

die() { echo "ошибка: $*" >&2; exit 1; }
need() { command -v "$1" >/dev/null || die "не найдена команда '$1'"; }

case "$arch" in
  amd64) bun_target="bun-linux-x64-baseline" ;;   # baseline: без требований к AVX2 на дешёвых VPS
  arm64) bun_target="bun-linux-arm64" ;;
  *) die "TARGET_ARCH должен быть amd64 или arm64, получено '$arch'" ;;
esac

mkdir -p "$build/$arch" "$build/.meta"

sha() { shasum -a 256 "$1" | cut -d' ' -f1; }
sha_dir() { (cd "$1" && find . -type f | LC_ALL=C sort | xargs shasum -a 256) | shasum -a 256 | cut -d' ' -f1; }

# Тег исходников omp должен совпадать с версией omp на Mac (протокол collab).
omp_tag() {
  if [ -n "${OMP_TAG:-}" ]; then echo "$OMP_TAG"; return; fi
  need omp
  echo "v$(omp --version | sed -E 's#^omp/##')"
}

omp_src() { # печатает путь к исходникам на нужном теге
  local tag="$1" dir="${OMP_SRC:-$build/src/oh-my-pi}" cur
  if [ ! -d "$dir/.git" ]; then
    git clone --depth 1 --branch "$tag" "$omp_repo" "$dir" >&2
  fi
  cur="$(git -C "$dir" describe --tags --exact-match 2>/dev/null)" || die "$dir не на теге (ожидался $tag)"
  [ "$cur" = "$tag" ] || die "$dir на теге $cur, ожидался $tag (удалите каталог или задайте OMP_SRC)"
  echo "$dir"
}

build_caddy() {
  need go
  echo "== caddy $caddy_version linux/$arch"
  local out="$build/$arch/caddy" mods
  # xcaddy ставим под хост (GOOS/GOARCH цели передаются только самой сборке)
  GOBIN="$build/tools" go install "github.com/caddyserver/xcaddy/cmd/xcaddy@$xcaddy_version"
  GOOS=linux GOARCH="$arch" CGO_ENABLED=0 \
    "$build/tools/xcaddy" build "$caddy_version" \
    --with github.com/mholt/caddy-ratelimit --with github.com/caddy-dns/duckdns --output "$out"
  mods="$(go version -m "$out")"
  printf '{"version":"%s","ratelimit":"%s","duckdns":"%s","sha256":"%s"}\n' "$caddy_version" \
    "$(awk '$2=="github.com/mholt/caddy-ratelimit"{print $3}' <<<"$mods")" \
    "$(awk '$2=="github.com/caddy-dns/duckdns"{print $3}' <<<"$mods")" \
    "$(sha "$out")" >"$build/.meta/caddy-$arch.json"
}

build_web() {
  need bun; need git
  local tag src dist="$build/omp-web" idx
  tag="$(omp_tag)"; src="$(omp_src "$tag")"
  echo "== веб-клиент omp $tag"
  (cd "$src" && bun install --filter @oh-my-pi/collab-web --frozen-lockfile)
  (cd "$src/packages/collab-web" && bun run build)
  rm -rf "$dist"
  cp -R "$src/packages/collab-web/dist" "$dist"
  idx="$dist/index.html"
  # Пост-обработка (docs/components/omp-relay.md): убрать аналитику и внешние canonical/OG.
  grep -q 'um\.can\.ac' "$idx" || die "в index.html нет ожидаемого тега um.can.ac: формат клиента изменился, проверьте пост-обработку"
  sed -i '' -E '/um\.can\.ac/d' "$idx"
  sed -i '' -E '/rel="canonical"/d;/property="og:url"/d' "$idx"
  ! grep -q 'um\.can\.ac' "$idx" || die "тег аналитики не удалился (многострочный?)"
  # Манифест и индексация: пути относительно манифеста работают под любым префиксом; robots закрываем.
  if [ -f "$dist/manifest.webmanifest" ]; then
    sed -i '' -E 's#"/#"./#g' "$dist/manifest.webmanifest"
  fi
  rm -f "$dist/sitemap.xml"
  printf 'User-agent: *\nDisallow: /\n' >"$dist/robots.txt"
  printf '{"omp_tag":"%s","sha256":"%s"}\n' "$tag" "$(sha_dir "$dist")" >"$build/.meta/web.json"
}

build_relay() {
  need bun; need git
  local tag src out="$build/$arch/omp-relay" i
  tag="$(omp_tag)"; src="$(omp_src "$tag")"
  echo "== relay $tag $bun_target"
  (cd "$src" && bun install --filter @oh-my-pi/collab-web --frozen-lockfile)
  # Загрузка runtime bun иногда обрывается (ConnectionClosed): повторяем, каждую ошибку показываем.
  for i in $(seq 1 "$bun_retries"); do
    if bun build --compile --target="$bun_target" "$src/packages/collab-web/scripts/local-relay.ts" --outfile "$out"; then
      break
    fi
    echo "попытка $i/$bun_retries не удалась" >&2
    [ "$i" -lt "$bun_retries" ] || die "сборка relay не удалась после $bun_retries попыток"
  done
  printf '{"omp_tag":"%s","bun":"%s","target":"%s","sha256":"%s"}\n' "$tag" "$(bun --version)" "$bun_target" \
    "$(sha "$out")" >"$build/.meta/relay-$arch.json"
}

write_manifest() {
  need python3
  python3 -I - "$build" <<'PY'
import glob, json, os, sys
b = sys.argv[1]
m = {"artifacts": {}}
for f in sorted(glob.glob(os.path.join(b, ".meta", "*.json"))):
    m["artifacts"][os.path.basename(f)[:-5]] = json.load(open(f))
json.dump(m, open(os.path.join(b, "manifest.json"), "w"), indent=2, ensure_ascii=False)
open(os.path.join(b, "manifest.json"), "a").write("\n")
PY
  echo "манифест: $build/manifest.json"
}

targets=("$@")
[ "${#targets[@]}" -gt 0 ] || targets=(all)
for t in "${targets[@]}"; do
  case "$t" in
    caddy) build_caddy ;;
    web) build_web ;;
    relay) build_relay ;;
    all) build_caddy; build_web; build_relay ;;
    *) die "неизвестная цель '$t' (caddy|web|relay|all)" ;;
  esac
done
write_manifest
