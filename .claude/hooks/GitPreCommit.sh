#!/bin/bash
# PreToolUse Git Commit Guard
# Runs before any Bash tool call; intercepts `git commit` to:
#   1. Check staged changes for sensitive data
#   2. Run tests
#   3. Suggest a commit message when -m is absent

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

# Only act when a git commit is in the command
if ! echo "$COMMAND" | grep -qE '(^|&&|\|)\s*git\s+commit'; then
    exit 0
fi

PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
[ -z "$PROJECT_ROOT" ] && exit 0
cd "$PROJECT_ROOT"

STAGED_DIFF=$(git diff --staged 2>/dev/null)
STAGED_FILES=$(git diff --staged --name-only 2>/dev/null)

if [ -z "$STAGED_FILES" ]; then
    echo "ℹ️  Nothing staged to commit."
    exit 0
fi

# ── 1. Sensitive-data scan ────────────────────────────────────────────────────
echo "🔍 Scanning staged changes for sensitive data..."

SENSITIVE_PATTERNS=(
    'sk-ant-[A-Za-z0-9_-]{20,}'          # Anthropic key
    'sk-[A-Za-z0-9]{40,}'                 # OpenAI key
    'eyJ[A-Za-z0-9_-]{30,}'               # JWT / Supabase anon/service key
    ' ANTHROPIC_API_KEY\s*=\s*[^#\n]{8,}'  # .env assignment
    'OPENAI_API_KEY\s*=\s*[^#\n]{8,}'
    'SUPABASE_(ANON|SERVICE)_KEY\s*=\s*[^#\n]{8,}'
    '-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY'
    'password\s*=\s*["\x27][^"\x27]{6,}'
    'secret\s*=\s*["\x27][^"\x27]{6,}'
)

SENSITIVE_HITS=()
for PATTERN in "${SENSITIVE_PATTERNS[@]}"; do
    MATCH=$(echo "$STAGED_DIFF" | grep -Pi "^\+.*($PATTERN)" 2>/dev/null | head -3)
    if [ -n "$MATCH" ]; then
        SENSITIVE_HITS+=("$MATCH")
    fi
done

if [ ${#SENSITIVE_HITS[@]} -gt 0 ]; then
    echo ""
    echo "🚨 COMMIT BLOCKED — Potential sensitive data in staged changes:"
    for HIT in "${SENSITIVE_HITS[@]}"; do
        echo "   $HIT"
    done
    echo ""
    echo "Remove or redact the above before committing."
    echo "If this is a false positive, add the file to .gitignore or use git update-index --assume-unchanged."
    exit 2
fi
echo "✅ No sensitive data detected."

# ── 2. Run tests ──────────────────────────────────────────────────────────────
echo ""
echo "🧪 Running tests before commit..."
TEST_FAILED=0

if command -v pytest &>/dev/null && [ -d "tests" ]; then
    echo "▶ pytest tests/ ..."
    if ! pytest tests/ -x -q --tb=short 2>&1; then
        TEST_FAILED=1
    fi
fi

if [ -f "package.json" ] && grep -q '"test"' package.json 2>/dev/null; then
    echo "▶ npm test ..."
    if ! npm test --silent 2>&1; then
        TEST_FAILED=1
    fi
fi

if [ $TEST_FAILED -eq 1 ]; then
    echo ""
    echo "❌ COMMIT BLOCKED — Fix failing tests first."
    exit 2
fi
echo "✅ All tests passed."

# ── 3. Suggest commit message when none provided ──────────────────────────────
if ! echo "$COMMAND" | grep -qE -- '-m\s'; then
    echo ""
    echo "💡 No -m flag detected. Analyzing staged changes for a suggested message..."

    STATS=$(git diff --staged --stat 2>/dev/null | tail -1)
    N_FILES=$(echo "$STAGED_FILES" | grep -c .)

    # Classify by file type
    HAS_TESTS=$(echo "$STAGED_FILES" | grep -cE '(test_|_test\.|spec\.)' 2>/dev/null || echo 0)
    HAS_DOCS=$(echo "$STAGED_FILES" | grep -cE '\.(md|rst|txt)$' 2>/dev/null || echo 0)
    HAS_CONFIG=$(echo "$STAGED_FILES" | grep -cE '\.(json|yaml|yml|toml|ini|cfg|sh)$' 2>/dev/null || echo 0)
    FIRST_FILE=$(echo "$STAGED_FILES" | head -1 | xargs basename 2>/dev/null)

    if [ "$HAS_TESTS" -gt 0 ] && [ "$N_FILES" -le 4 ]; then
        SCOPE=$(echo "$STAGED_FILES" | grep -E '(test_|_test\.)' | head -1 | xargs basename | sed 's/test_//;s/_test.*//' 2>/dev/null)
        SUGGESTED="test: add/update tests for ${SCOPE:-$FIRST_FILE}"
    elif [ "$HAS_DOCS" -gt 0 ] && [ "$N_FILES" -le 3 ]; then
        SUGGESTED="docs: update $FIRST_FILE"
    elif [ "$HAS_CONFIG" -gt 0 ] && [ "$N_FILES" -le 2 ]; then
        SUGGESTED="chore: update configuration ($FIRST_FILE)"
    elif [ "$N_FILES" -eq 1 ]; then
        SUGGESTED="feat: update $FIRST_FILE"
    else
        FILE_LIST=$(echo "$STAGED_FILES" | head -3 | xargs -I{} basename {} | tr '\n' ', ' | sed 's/,$//')
        SUGGESTED="feat: update $FILE_LIST"
    fi

    echo ""
    echo "📝 Suggested commit message ($STATS):"
    echo "   $SUGGESTED"
    echo ""
    echo "Staged files:"
    echo "$STAGED_FILES" | sed 's/^/   - /'
    echo ""
    echo "COMMIT BLOCKED — Re-run with: git commit -m '$SUGGESTED'"
    echo "(Edit the suggested message as needed.)"
    exit 2
fi

exit 0
