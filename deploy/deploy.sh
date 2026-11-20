#!/usr/bin/env bash
# 把 build.py 的产物发布到服务器。
#
#   bash deploy/deploy.sh <user@host> [远程目录]
#
# 默认远程目录 /var/www/prompt.guanjihuan.com，与 deploy/nginx.conf 里的 root 一致。
set -euo pipefail

TARGET="${1:-}"
REMOTE_DIR="${2:-/var/www/prompt.guanjihuan.com}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -z "$TARGET" ]; then
  echo "用法：bash deploy/deploy.sh <user@host> [远程目录]" >&2
  exit 2
fi

echo "[deploy] 本地构建…"
python "$ROOT/build.py"

echo "[deploy] 上传到 $TARGET:$REMOTE_DIR …"
ssh "$TARGET" "mkdir -p '$REMOTE_DIR'"
rsync -av --delete "$ROOT/dist/" "$TARGET:$REMOTE_DIR/"

echo "[deploy] 远端校验…"
ssh "$TARGET" "ls -la '$REMOTE_DIR' && test -f '$REMOTE_DIR/index.html' && test -f '$REMOTE_DIR/404.html'"

echo "[deploy] 完成：https://prompt.guanjihuan.com/"
