#!/bin/bash
# PostToolUse Git Changelog Hook
# Runs after every Bash tool call; when the command was a git commit,
# appends an entry to CHANGELOG.md under [Unreleased].

INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)

# Only act on git commit commands
if ! echo "$COMMAND" | grep -qE '(^|&&|\|)\s*git\s+commit'; then
    exit 0
fi

PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
[ -z "$PROJECT_ROOT" ] && exit 0
cd "$PROJECT_ROOT"

# Confirm the commit actually succeeded by verifying HEAD changed
COMMIT_HASH=$(git rev-parse --short HEAD 2>/dev/null)
[ -z "$COMMIT_HASH" ] && exit 0

# Avoid double-writing: check if this hash is already in the log
CHANGELOG="$PROJECT_ROOT/CHANGELOG.md"
if [ -f "$CHANGELOG" ] && grep -q "$COMMIT_HASH" "$CHANGELOG" 2>/dev/null; then
    exit 0
fi

COMMIT_MSG=$(git log -1 --pretty=format:"%s" 2>/dev/null)
COMMIT_DATE=$(date '+%Y-%m-%d')
CHANGED_FILES=$(git diff-tree --no-commit-id -r --name-only HEAD 2>/dev/null | head -5 | tr '\n' ', ' | sed 's/,\s*$//')
AUTHOR=$(git log -1 --pretty=format:"%an" 2>/dev/null)

# ── Bootstrap CHANGELOG.md if absent ─────────────────────────────────────────
if [ ! -f "$CHANGELOG" ]; then
    cat > "$CHANGELOG" <<'EOF'
# Changelog

All notable changes to DocuMind are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

EOF
    echo "📋 Created CHANGELOG.md"
fi

# Ensure [Unreleased] section exists
if ! grep -q "## \[Unreleased\]" "$CHANGELOG"; then
    sed -i '1s/^/## [Unreleased]\n\n/' "$CHANGELOG"
fi

# ── Build the entry ───────────────────────────────────────────────────────────
# Classify by conventional-commit prefix
PREFIX=$(echo "$COMMIT_MSG" | grep -oP '^(feat|fix|docs|test|chore|refactor|perf|ci|style)' 2>/dev/null || echo "change")
case "$PREFIX" in
    feat)     SECTION="### Added" ;;
    fix)      SECTION="### Fixed" ;;
    docs)     SECTION="### Documentation" ;;
    test)     SECTION="### Tests" ;;
    refactor) SECTION="### Changed" ;;
    perf)     SECTION="### Performance" ;;
    *)        SECTION="### Changed" ;;
esac

ENTRY="- \`$COMMIT_HASH\` $COMMIT_MSG ($COMMIT_DATE)"
[ -n "$CHANGED_FILES" ] && ENTRY="$ENTRY — *$CHANGED_FILES*"

# Insert under [Unreleased], creating the section header if needed
if grep -q "$SECTION" "$CHANGELOG"; then
    # Append under existing section header
    sed -i "/$SECTION/a\\$ENTRY" "$CHANGELOG"
else
    # Insert section + entry right after [Unreleased]
    sed -i "/## \[Unreleased\]/a\\\\n$SECTION\\n$ENTRY" "$CHANGELOG"
fi

echo "📋 CHANGELOG.md updated → $COMMIT_HASH: $COMMIT_MSG"

exit 0
