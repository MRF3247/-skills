#!/usr/bin/env bash
# Verify the MiniMax image_gen plugin end-to-end WITHOUT printing the API key.
# Usage: bash verify_minimax.sh [output_dir]   (default: current dir)
# Places the generated test image in output_dir; delete it after checking.
# Pattern transfers to any provider: swap endpoint/headers/body.
set -u
OUT="${1:-$(pwd)}"
ENV_FILE="${HOME}/.hermes/.env"

echo "== config =="
hermes config get image_gen 2>/dev/null || echo "(hermes config get failed - is hermes on PATH?)"

echo "== plugin dir =="
ls -1 "${HOME}/.hermes/plugins/image_gen/minimax/" 2>/dev/null || echo "MISSING plugin dir"

echo "== key presence (names only, values hidden) =="
grep -oE "MINIMAX_[A-Z_]*=" "$ENV_FILE" 2>/dev/null | sort -u || echo "no MINIMAX vars in $ENV_FILE"

KEY=$(grep -E "^MINIMAX_CN_API_KEY=" "$ENV_FILE" | cut -d= -f2- | tr -d '"' | tr -d "'")
if [ -z "$KEY" ]; then echo "!! MINIMAX_CN_API_KEY empty - aborting"; exit 1; fi
echo "key length: ${#KEY} (value hidden)"

echo "== endpoint reachability (any http code = reachable; 404 on root is normal) =="
curl -s -o /dev/null -w "http=%{http_code} time=%{time_total}s\n" --connect-timeout 8 https://api.minimaxi.com

echo "== real generation probe (~18s) =="
RESP=$(curl -s --connect-timeout 10 --max-time 90 -X POST "https://api.minimaxi.com/v1/image_generation" \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"image-01","prompt":"a red apple on a wooden table","n":1,"aspect_ratio":"1:1"}')

echo "$RESP" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
except Exception:
    print('unparseable/empty response - network jitter? retry the script')
    sys.exit(0)
b = d.get('base_resp', {})
print('status:', b.get('status_code'), b.get('status_msg'))
print('success_count:', d.get('metadata', {}).get('success_count'))
" 2>/dev/null

URL=$(echo "$RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['image_urls'][0])" 2>/dev/null)
if [ -n "$URL" ]; then
  mkdir -p "$OUT"
  DEST="$OUT/minimax_verify_$(date +%Y%m%d_%H%M%S).jpg"
  curl -s -o "$DEST" -w "downloaded %{size_download}B -> $DEST\n" "$URL"
  echo "done. test artifact: $DEST (delete after checking)"
else
  echo "no image URL returned - see status line above"
fi
