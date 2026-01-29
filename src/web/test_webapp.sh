#!/bin/bash
# Web UI Functional Test Script
# Uses agent-browser to test the Agent Management Suite web UI

BASE_URL="http://127.0.0.1:8000"
PASS=0
FAIL=0

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASS++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAIL++))
}

log_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Start fresh
log_info "Starting web UI functional tests..."
agent-browser close 2>/dev/null || true
sleep 1

# ============================================
# Test 1: Dashboard loads
# ============================================
log_info "Test 1: Dashboard loads"
OUTPUT=$(agent-browser open "$BASE_URL/" 2>&1)
# Try once more if first attempt fails (cold start)
if ! echo "$OUTPUT" | grep -q "Dashboard"; then
    sleep 1
    OUTPUT=$(agent-browser open "$BASE_URL/" 2>&1)
fi
if echo "$OUTPUT" | grep -q "Dashboard"; then
    log_pass "Dashboard loads"
else
    log_fail "Dashboard failed to load"
fi

# ============================================
# Test 2: Dashboard has stats cards
# ============================================
log_info "Test 2: Dashboard has stats cards"
SNAPSHOT=$(agent-browser snapshot -i 2>&1)
if echo "$SNAPSHOT" | grep -q "Agents\|agents"; then
    log_pass "Stats cards present"
else
    log_fail "Stats cards missing"
fi

# ============================================
# Test 3: Navigate to Agents page
# ============================================
log_info "Test 3: Navigate to Agents page"
if agent-browser open "$BASE_URL/agents" 2>&1 | grep -q "Agents"; then
    log_pass "Agents page loads"
else
    log_fail "Agents page failed"
fi

# ============================================
# Test 4: Agents list is populated
# ============================================
log_info "Test 4: Agents list is populated"
CONTENT=$(agent-browser eval "document.body.innerText" 2>&1)
if echo "$CONTENT" | grep -q "agents loaded"; then
    log_pass "Agents list populated"
else
    log_fail "Agents list empty"
fi

# ============================================
# Test 5: Agent detail page
# ============================================
log_info "Test 5: Agent detail page"
if agent-browser open "$BASE_URL/agents/python-dev" 2>&1 | grep -q "python-dev"; then
    log_pass "Agent detail loads"
else
    log_fail "Agent detail failed"
fi

# ============================================
# Test 6: Agent has exclusion toggle
# ============================================
log_info "Test 6: Agent has exclusion toggle"
SNAPSHOT=$(agent-browser snapshot -i 2>&1)
if echo "$SNAPSHOT" | grep -qi "exclude\|include"; then
    log_pass "Exclusion toggle present"
else
    log_fail "Exclusion toggle missing"
fi

# ============================================
# Test 7: Skills page loads
# ============================================
log_info "Test 7: Skills page loads"
if agent-browser open "$BASE_URL/skills" 2>&1 | grep -q "Skills"; then
    log_pass "Skills page loads"
else
    log_fail "Skills page failed"
fi

# ============================================
# Test 8: Plugins page loads
# ============================================
log_info "Test 8: Plugins page loads"
if agent-browser open "$BASE_URL/plugins" 2>&1 | grep -q "Plugins"; then
    log_pass "Plugins page loads"
else
    log_fail "Plugins page failed"
fi

# ============================================
# Test 9: Hooks page loads
# ============================================
log_info "Test 9: Hooks page loads"
if agent-browser open "$BASE_URL/hooks" 2>&1 | grep -q "Hooks"; then
    log_pass "Hooks page loads"
else
    log_fail "Hooks page failed"
fi

# ============================================
# Test 10: Sync page loads
# ============================================
log_info "Test 10: Sync page loads"
if agent-browser open "$BASE_URL/sync" 2>&1 | grep -q "Sync"; then
    log_pass "Sync page loads"
else
    log_fail "Sync page failed"
fi

# ============================================
# Test 11: Sync page shows platforms
# ============================================
log_info "Test 11: Sync page shows platforms"
CONTENT=$(agent-browser eval "document.body.innerText" 2>&1)
if echo "$CONTENT" | grep -q "Codex CLI"; then
    log_pass "Platform cards present"
else
    log_fail "Platform cards missing"
fi

# ============================================
# Test 12: Take screenshots
# ============================================
log_info "Test 12: Taking screenshots"
mkdir -p /tmp/webapp-screenshots

agent-browser open "$BASE_URL/" >/dev/null 2>&1
agent-browser screenshot /tmp/webapp-screenshots/dashboard.png --full >/dev/null 2>&1

agent-browser open "$BASE_URL/agents" >/dev/null 2>&1
agent-browser screenshot /tmp/webapp-screenshots/agents.png --full >/dev/null 2>&1

agent-browser open "$BASE_URL/sync" >/dev/null 2>&1
agent-browser screenshot /tmp/webapp-screenshots/sync.png --full >/dev/null 2>&1

if [ -f /tmp/webapp-screenshots/dashboard.png ]; then
    log_pass "Screenshots saved to /tmp/webapp-screenshots/"
else
    log_fail "Screenshots failed"
fi

# ============================================
# Cleanup
# ============================================
agent-browser close >/dev/null 2>&1

# ============================================
# Summary
# ============================================
echo ""
echo "============================================"
echo "TEST SUMMARY"
echo "============================================"
echo -e "${GREEN}Passed: $PASS${NC}"
echo -e "${RED}Failed: $FAIL${NC}"
TOTAL=$((PASS + FAIL))
echo "Total:  $TOTAL"
echo "============================================"

if [ $FAIL -gt 0 ]; then
    exit 1
else
    exit 0
fi
