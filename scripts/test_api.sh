#!/bin/bash

# Wrong Opinions API Test Script
# Tests all API endpoints in a logical workflow
#
# IMPORTANT: For best results, start with an empty database
# If you see a 409 error on user registration, reset the database:
#   rm wrong_opinions.db
#   uv run alembic upgrade head
# Then restart the API server before running this script.
#
# Usage: ./scripts/test_api.sh
# Or with custom URL: API_BASE_URL=http://server:8000 ./scripts/test_api.sh

set -e  # Exit on error (disabled for individual tests)
set +e  # Allow continuing after failures

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_URL="${API_BASE_URL:-http://localhost:8000}"
TOKEN=""
USER_ID=""
TMDB_ID=""
MUSICBRAINZ_ID=""
WEEK_ID=""
CURRENT_WEEK_ID=""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Global variable to store last response body
LAST_BODY=""

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

# Print section header
section() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC} ${BOLD}$1${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Make API call and display results
# Stores response body in global LAST_BODY variable
call_api() {
    local method=$1
    local endpoint=$2
    local data=$3
    local auth=$4
    local description=$5

    TESTS_RUN=$((TESTS_RUN + 1))

    echo -e "${BLUE}────────────────────────────────────────────────────────────────────────${NC}"
    echo -e "${YELLOW}${BOLD}TEST $TESTS_RUN: $description${NC}"
    echo -e "${YELLOW}Endpoint:${NC} $method $endpoint"

    if [ -n "$data" ]; then
        echo -e "${YELLOW}Request Body:${NC}"
        echo "$data" | jq '.' 2>/dev/null || echo "$data"
    fi
    echo ""

    # Build curl command
    local curl_cmd="curl -s -w '\nHTTP_STATUS:%{http_code}' -X $method"

    if [ "$auth" = "true" ]; then
        curl_cmd="$curl_cmd -H 'Authorization: Bearer $TOKEN'"
    fi

    if [ -n "$data" ]; then
        curl_cmd="$curl_cmd -H 'Content-Type: application/json' -d '$data'"
    fi

    curl_cmd="$curl_cmd '$BASE_URL$endpoint'"

    # Execute
    local response
    response=$(eval $curl_cmd 2>&1)
    local http_status
    http_status=$(echo "$response" | grep "HTTP_STATUS:" | cut -d: -f2)
    LAST_BODY=$(echo "$response" | sed '/HTTP_STATUS:/d')

    # Display response
    if [[ $http_status -ge 200 && $http_status -lt 300 ]]; then
        echo -e "${GREEN}✓ Status: $http_status${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}✗ Status: $http_status${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi

    echo -e "${YELLOW}Response:${NC}"
    echo "$LAST_BODY" | jq '.' 2>/dev/null || echo "$LAST_BODY"
    echo ""
}

# ============================================================================
# TEST EXECUTION
# ============================================================================

echo ""
echo -e "${BOLD}${CYAN}╔════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║                    WRONG OPINIONS API TEST SUITE                       ║${NC}"
echo -e "${BOLD}${CYAN}╚════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Base URL:${NC} $BASE_URL"
echo -e "${YELLOW}Started:${NC} $(date)"
echo ""

# ============================================================================
# 1. PUBLIC ENDPOINTS (NO AUTH)
# ============================================================================

section "1. PUBLIC ENDPOINTS (No Authentication Required)"

# Test 1: Health Check
call_api "GET" "/health" "" "false" "Health Check"

# Test 2: Register User
register_data='{
  "username": "testuser",
  "email": "test@example.com",
  "password": "testpassword123"
}'
call_api "POST" "/api/auth/register" "$register_data" "false" "Register New User"
USER_ID=$(echo "$LAST_BODY" | jq -r '.id' 2>/dev/null)
echo -e "${CYAN}➜ Extracted User ID: $USER_ID${NC}"
echo ""

# Test 3: Login
login_data='{
  "username": "testuser",
  "password": "testpassword123"
}'
call_api "POST" "/api/auth/login" "$login_data" "false" "Login and Get Token"
TOKEN=$(echo "$LAST_BODY" | jq -r '.access_token' 2>/dev/null)
echo -e "${CYAN}➜ Extracted Token: ${TOKEN:0:50}...${NC}"
echo ""

# ============================================================================
# 2. AUTHENTICATION ENDPOINTS
# ============================================================================

section "2. AUTHENTICATION ENDPOINTS"

# Test 4: Get Current User
call_api "GET" "/api/auth/me" "" "true" "Get Current User Info"

# ============================================================================
# 3. MOVIE ENDPOINTS
# ============================================================================

section "3. MOVIE ENDPOINTS"

# Test 5: Search Movies
call_api "GET" "/api/movies/search?query=Inception" "" "true" "Search Movies (query: Inception)"
TMDB_ID=$(echo "$LAST_BODY" | jq -r '.results[0].tmdb_id' 2>/dev/null)
echo -e "${CYAN}➜ Extracted TMDB ID from first result: $TMDB_ID${NC}"
echo ""

# Test 6: Get Movie Details
if [ -n "$TMDB_ID" ] && [ "$TMDB_ID" != "null" ]; then
    call_api "GET" "/api/movies/$TMDB_ID" "" "true" "Get Movie Details (TMDB ID: $TMDB_ID)"

    # Test 7: Get Movie Credits
    call_api "GET" "/api/movies/$TMDB_ID/credits?limit=5" "" "true" "Get Movie Credits (limit: 5)"
else
    echo -e "${RED}⚠ Skipping movie details and credits tests (no TMDB ID)${NC}"
fi

# ============================================================================
# 4. ALBUM ENDPOINTS
# ============================================================================

section "4. ALBUM ENDPOINTS"

echo -e "${YELLOW}Note: Adding 1-second delay for MusicBrainz rate limiting...${NC}"
sleep 1

# Test 8: Search Albums
call_api "GET" "/api/albums/search?query=Dark+Side" "" "true" "Search Albums (query: Dark Side)"
MUSICBRAINZ_ID=$(echo "$LAST_BODY" | jq -r '.results[0].musicbrainz_id' 2>/dev/null)
echo -e "${CYAN}➜ Extracted MusicBrainz ID from first result: $MUSICBRAINZ_ID${NC}"
echo ""

sleep 1

# Test 9: Get Album Details
if [ -n "$MUSICBRAINZ_ID" ] && [ "$MUSICBRAINZ_ID" != "null" ]; then
    call_api "GET" "/api/albums/$MUSICBRAINZ_ID" "" "true" "Get Album Details (MusicBrainz ID: $MUSICBRAINZ_ID)"

    sleep 1

    # Test 10: Get Album Credits
    call_api "GET" "/api/albums/$MUSICBRAINZ_ID/credits?limit=3" "" "true" "Get Album Credits (limit: 3)"
else
    echo -e "${RED}⚠ Skipping album details and credits tests (no MusicBrainz ID)${NC}"
fi

# ============================================================================
# 5. WEEK ENDPOINTS
# ============================================================================

section "5. WEEK ENDPOINTS"

# Test 11: Get/Create Current Week
call_api "GET" "/api/weeks/current" "" "true" "Get or Create Current Week"
CURRENT_WEEK_ID=$(echo "$LAST_BODY" | jq -r '.id' 2>/dev/null)
echo -e "${CYAN}➜ Current Week ID: $CURRENT_WEEK_ID${NC}"
echo ""

# Test 12: Create Specific Week (Week 1 of 2024)
create_week_data='{
  "year": 2024,
  "week_number": 1,
  "notes": "First week of 2024 - Testing API"
}'
call_api "POST" "/api/weeks" "$create_week_data" "true" "Create Specific Week (2024, Week 1)"
WEEK_ID=$(echo "$LAST_BODY" | jq -r '.id' 2>/dev/null)
echo -e "${CYAN}➜ Created Week ID: $WEEK_ID${NC}"
echo ""

# Test 13: List All Weeks
call_api "GET" "/api/weeks?page=1&page_size=10" "" "true" "List All Weeks (page 1)"

# Test 14: Get Specific Week
if [ -n "$WEEK_ID" ] && [ "$WEEK_ID" != "null" ]; then
    call_api "GET" "/api/weeks/$WEEK_ID" "" "true" "Get Week Details (Week ID: $WEEK_ID)"
fi

# ============================================================================
# 6. ADD SELECTIONS TO WEEK
# ============================================================================

section "6. ADD MOVIES AND ALBUMS TO WEEK"

# Test 15: Add First Movie
if [ -n "$WEEK_ID" ] && [ "$WEEK_ID" != "null" ] && [ -n "$TMDB_ID" ] && [ "$TMDB_ID" != "null" ]; then
    add_movie_data="{
  \"tmdb_id\": $TMDB_ID,
  \"position\": 1
}"
    call_api "POST" "/api/weeks/$WEEK_ID/movies" "$add_movie_data" "true" "Add Movie to Week (Position 1)"
else
    echo -e "${RED}⚠ Skipping add movie test (missing Week ID or TMDB ID)${NC}"
fi

# Test 16: Add Second Movie (search for another movie first)
call_api "GET" "/api/movies/search?query=Matrix" "" "true" "Search for Second Movie (Matrix)"
TMDB_ID_2=$(echo "$LAST_BODY" | jq -r '.results[0].tmdb_id' 2>/dev/null)
echo -e "${CYAN}➜ Second Movie TMDB ID: $TMDB_ID_2${NC}"
echo ""

if [ -n "$WEEK_ID" ] && [ "$WEEK_ID" != "null" ] && [ -n "$TMDB_ID_2" ] && [ "$TMDB_ID_2" != "null" ]; then
    add_movie_data_2="{
  \"tmdb_id\": $TMDB_ID_2,
  \"position\": 2
}"
    call_api "POST" "/api/weeks/$WEEK_ID/movies" "$add_movie_data_2" "true" "Add Second Movie to Week (Position 2)"
fi

sleep 1

# Test 17: Add Album
if [ -n "$WEEK_ID" ] && [ "$WEEK_ID" != "null" ] && [ -n "$MUSICBRAINZ_ID" ] && [ "$MUSICBRAINZ_ID" != "null" ]; then
    add_album_data="{
  \"musicbrainz_id\": \"$MUSICBRAINZ_ID\",
  \"position\": 1
}"
    call_api "POST" "/api/weeks/$WEEK_ID/albums" "$add_album_data" "true" "Add Album to Week (Position 1)"
fi

# ============================================================================
# 7. UPDATE AND RETRIEVE WEEK
# ============================================================================

section "7. UPDATE AND RETRIEVE WEEK WITH SELECTIONS"

# Test 18: Update Week Notes
if [ -n "$WEEK_ID" ] && [ "$WEEK_ID" != "null" ]; then
    update_notes_data='{
  "notes": "Updated notes - Movies and album added successfully!"
}'
    call_api "PATCH" "/api/weeks/$WEEK_ID" "$update_notes_data" "true" "Update Week Notes"

    # Test 19: Get Updated Week with Selections
    call_api "GET" "/api/weeks/$WEEK_ID" "" "true" "Get Updated Week with All Selections"
fi

# ============================================================================
# 8. REMOVE SELECTIONS
# ============================================================================

section "8. REMOVE SELECTIONS FROM WEEK"

# Test 20: Remove Movie from Position 2
if [ -n "$WEEK_ID" ] && [ "$WEEK_ID" != "null" ]; then
    call_api "DELETE" "/api/weeks/$WEEK_ID/movies/2" "" "true" "Remove Movie from Position 2"
fi

sleep 1

# Test 21: Remove Album from Position 1
if [ -n "$WEEK_ID" ] && [ "$WEEK_ID" != "null" ]; then
    call_api "DELETE" "/api/weeks/$WEEK_ID/albums/1" "" "true" "Remove Album from Position 1"
fi

# ============================================================================
# 9. DELETE WEEK
# ============================================================================

section "9. DELETE WEEK"

# Test 22: Delete Week
if [ -n "$WEEK_ID" ] && [ "$WEEK_ID" != "null" ]; then
    call_api "DELETE" "/api/weeks/$WEEK_ID" "" "true" "Delete Week (Week ID: $WEEK_ID)"
fi

# ============================================================================
# 10. ERROR CASES
# ============================================================================

section "10. ERROR CASE TESTING"

# Test 23: Try to create duplicate week (should return 409)
duplicate_week_data='{
  "year": 2024,
  "week_number": 52,
  "notes": "First attempt"
}'
call_api "POST" "/api/weeks" "$duplicate_week_data" "true" "Create Week (2024, Week 52)"

# Try to create the same week again
call_api "POST" "/api/weeks" "$duplicate_week_data" "true" "Attempt to Create Duplicate Week (Expect 409)"

# Test 24: Unauthenticated request (should return 401)
echo -e "${YELLOW}Note: Temporarily removing authentication for this test...${NC}"
call_api "GET" "/api/movies/search?query=test" "" "false" "Unauthenticated Request (Expect 401)"

# ============================================================================
# SUMMARY
# ============================================================================

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                            TEST SUMMARY                                ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BOLD}Total Tests Run:${NC}    $TESTS_RUN"
echo -e "${GREEN}${BOLD}Tests Passed:${NC}      $TESTS_PASSED"
echo -e "${RED}${BOLD}Tests Failed:${NC}      $TESTS_FAILED"
echo ""
echo -e "${YELLOW}Finished:${NC}          $(date)"
echo -e "${YELLOW}Base URL:${NC}          $BASE_URL"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}${BOLD}✓ ALL TESTS PASSED!${NC}"
    exit 0
else
    echo -e "${RED}${BOLD}✗ SOME TESTS FAILED${NC}"
    exit 1
fi
