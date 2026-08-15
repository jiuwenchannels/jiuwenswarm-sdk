#!/usr/bin/env bash
# Process and system memory statistics, and context-window token usage.
# Requires the gateway to be running: jiuwenswarm serve
#   HTTP: http://localhost:19001

BASE="http://localhost:19001"

# ---------------------------------------------------------------------------
# 1. Memory stats
#    GET /v1/memory returns RSS of the gateway process and system RAM info.
# ---------------------------------------------------------------------------
echo "=== Gateway memory usage ==="
curl -s "$BASE/v1/memory" | python3 -c "
import json, sys
d = json.load(sys.stdin)
rss   = d.get('process_rss_mb', 0)
total = d.get('system_total_mb', 0)
free  = d.get('system_free_mb', 0)
used  = total - free
pct   = round(used / total * 100, 1) if total else 0
print(f'  Gateway RSS      : {rss:.1f} MB')
print(f'  System RAM total : {total:.0f} MB')
print(f'  System RAM free  : {free:.0f} MB')
print(f'  System RAM used  : {used:.0f} MB  ({pct}%)')
ctx = d.get('context_tokens')
if ctx is not None:
    print(f'  Context tokens   : {ctx:,}')
"

# ---------------------------------------------------------------------------
# 2. Token usage for the current session
#    GET /v1/usage returns cumulative prompt/completion/total token counts.
# ---------------------------------------------------------------------------
echo ""
echo "=== Token usage ==="
curl -s "$BASE/v1/usage" | python3 -c "
import json, sys
d = json.load(sys.stdin)
prompt     = d.get('prompt_tokens', 0)
completion = d.get('completion_tokens', 0)
total      = d.get('total_tokens', 0)
print(f'  Prompt tokens     : {prompt:,}')
print(f'  Completion tokens : {completion:,}')
print(f'  Total tokens      : {total:,}')
" 2>/dev/null || echo "  (usage endpoint not available)"

# ---------------------------------------------------------------------------
# 3. Continuous monitoring — sample every 5 s for 3 samples
# ---------------------------------------------------------------------------
echo ""
echo "=== Memory sampling (3 × 5 s) ==="
for i in 1 2 3; do
  RSS=$(curl -s "$BASE/v1/memory" | python3 -c "import json,sys; print(json.load(sys.stdin).get('process_rss_mb', 'n/a'))")
  echo "  sample $i: RSS = ${RSS} MB"
  [ "$i" -lt 3 ] && sleep 5
done
