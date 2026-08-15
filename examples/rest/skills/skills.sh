#!/usr/bin/env bash
# Skills management via REST: list installed skills and toggle them on/off.
# Requires the gateway to be running: jiuwenswarm serve
#   HTTP: http://localhost:19001

BASE="http://localhost:19001"

# ---------------------------------------------------------------------------
# 1. List all installed skills
# ---------------------------------------------------------------------------
echo "=== List skills ==="
SKILLS_JSON=$(curl -s "$BASE/v1/skills")
echo "$SKILLS_JSON" | python3 -m json.tool

# Pretty-print skill names and their current enabled state.
echo ""
echo "--- Skill summary ---"
echo "$SKILLS_JSON" | python3 -c "
import json, sys
skills = json.load(sys.stdin).get('skills', [])
if not skills:
    print('  (no skills installed)')
for s in skills:
    state = 'enabled ' if s.get('enabled') else 'disabled'
    print(f\"  [{state}] {s['id']:30s} {s.get('name','')}\")
"

# Extract the first skill ID for the toggle demo below.
SKILL_ID=$(echo "$SKILLS_JSON" | python3 -c "
import json, sys
skills = json.load(sys.stdin).get('skills', [])
print(skills[0]['id'] if skills else '')
")

if [ -z "$SKILL_ID" ]; then
  echo ""
  echo "No skills found — skipping toggle demo."
  exit 0
fi

CURRENT_STATE=$(echo "$SKILLS_JSON" | python3 -c "
import json, sys
skills = json.load(sys.stdin).get('skills', [])
print(str(skills[0].get('enabled', True)).lower() if skills else 'true')
")
# Toggle: if currently enabled → disable; if disabled → enable.
NEW_STATE="true"
if [ "$CURRENT_STATE" = "true" ]; then NEW_STATE="false"; fi

# ---------------------------------------------------------------------------
# 2. Toggle a skill
# ---------------------------------------------------------------------------
echo ""
echo "=== Toggle skill '$SKILL_ID' (enabled → $NEW_STATE) ==="
curl -s -X PATCH "$BASE/v1/skills/$SKILL_ID" \
  -H "Content-Type: application/json" \
  -d "{\"enabled\": $NEW_STATE}" \
  | python3 -m json.tool

# ---------------------------------------------------------------------------
# 3. Confirm the new state
# ---------------------------------------------------------------------------
echo ""
echo "=== Confirm skill state after toggle ==="
curl -s "$BASE/v1/skills/$SKILL_ID" | python3 -m json.tool

# ---------------------------------------------------------------------------
# 4. Restore the original state
# ---------------------------------------------------------------------------
echo ""
echo "=== Restore original state ($CURRENT_STATE) ==="
curl -s -X PATCH "$BASE/v1/skills/$SKILL_ID" \
  -H "Content-Type: application/json" \
  -d "{\"enabled\": $CURRENT_STATE}" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(f\"  restored: {d.get('id')} enabled={d.get('enabled')}\")"
