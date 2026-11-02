#!/usr/bin/env bash
# auth 모듈과 공통 동작의 HTTP smoke 테스트. 실행 중인 서버에 요청을 보내 기대 상태 코드와 비교한다.
#   BASE=http://localhost:8001 bash .claude/skills/fastapi-run/scripts/smoke_auth.sh
# 매번 새 이메일로 가입하므로 반복 실행해도 된다. 하나라도 FAIL이면 종료코드 1.
set -u

BASE="${BASE:-http://localhost:8001}"
TS="$(date +%s)$$"
EMAIL="smoke_${TS}@example.com"
PW="password123"
TMPD="$(mktemp -d "${TMPDIR:-/tmp}/smoke.XXXXXX")"
trap 'rm -rf "$TMPD"' EXIT
HDR="$TMPD/hdr"; BODY="$TMPD/body"
PASS=0; FAIL=0; FAILED=()

json() { # 파이썬 식으로 본문 JSON(d)을 평가해 출력
  python3 -c "import json,sys
try: d=json.load(open('$BODY'))
except Exception: d=None
print($1)" 2>/dev/null
}

# check 이름 기대코드 메서드 경로 [curl 인자...]
check() {
  local name=$1 want=$2 m=$3 p=$4; shift 4
  local got
  : > "$BODY"
  got=$(curl -s -D "$HDR" -o "$BODY" -w '%{http_code}' -X "$m" "$BASE$p" "$@")
  if [ "$got" = "$want" ]; then
    PASS=$((PASS+1)); printf 'PASS  %-34s %s %s -> %s\n' "$name" "$m" "$p" "$got"
    return 0
  fi
  FAIL=$((FAIL+1)); FAILED+=("$name")
  printf 'FAIL  %-34s %s %s -> %s (기대 %s)\n' "$name" "$m" "$p" "$got" "$want"
  printf '      %s\n' "$(head -c 300 "$BODY")"
  return 1
}

# 직전 응답의 추가 조건. expect 이름 조건식(파이썬, d=본문)
expect() {
  local name=$1 cond=$2
  if [ "$(json "bool($cond)")" = "True" ]; then
    PASS=$((PASS+1)); printf 'PASS  %s\n' "$name"
  else
    FAIL=$((FAIL+1)); FAILED+=("$name")
    printf 'FAIL  %-34s %s\n      %s\n' "$name" "$cond" "$(head -c 300 "$BODY")"
  fi
}

# 공통 에러 형식 {"success": false, "error_code", "message"}와 error_code 확인
err() { expect "  ↳ error_code=$1" "d and d.get('success') is False and d.get('error_code')=='$1' and bool(d.get('message'))"; }

bearer_header() {
  if grep -qi '^www-authenticate: *bearer' "$HDR"; then
    PASS=$((PASS+1)); printf 'PASS  %-34s\n' "  ↳ WWW-Authenticate: Bearer"
  else
    FAIL=$((FAIL+1)); FAILED+=("WWW-Authenticate($1)"); printf 'FAIL  %-34s 헤더 없음\n' "  ↳ WWW-Authenticate: Bearer"
  fi
}

J=(-H "Content-Type: application/json")
echo "BASE=$BASE  EMAIL=$EMAIL"
if ! curl -s -o /dev/null "$BASE/"; then
  echo "FAIL  서버에 연결할 수 없습니다 ($BASE). run_server.sh start로 먼저 띄우세요."
  exit 1
fi

echo "--- 기본"
check "루트" 200 GET /
check "DB 연결" 200 GET /health/db
check "Swagger" 200 GET /docs
check "OpenAPI" 200 GET /openapi.json
expect "  ↳ auth 경로 5개 등록" "all(k in d['paths'] for k in ['/v1/auth/signup','/v1/auth/login','/v1/auth/logout','/v1/users/me','/v1/users/me/points'])"
python3 - "$BODY" <<'PY'
import json, sys
paths = json.load(open(sys.argv[1]))["paths"]
for mod, prefix in [("stores", "/v1/stores"), ("catalog", "/v1/products"), ("catalog", "/v1/offers"),
                    ("reservations", "/v1/reservations"), ("payments", "/v1/payments")]:
    state = "구현" if any(p.startswith(prefix) for p in paths) else "미구현"
    print(f"INFO  {mod:<12} {prefix:<18} {state}")
PY
check "없는 경로" 404 GET /v1/nope; err NOT_FOUND

echo "--- 회원가입"
check "가입 CUSTOMER" 201 POST /v1/auth/signup "${J[@]}" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PW\",\"name\":\"스모크\",\"phone\":\"010-0000-0000\",\"role\":\"CUSTOMER\"}"
expect "  ↳ 응답에 password 없음" "d and 'id' in d and not any('password' in k for k in d)"
check "가입 중복" 409 POST /v1/auth/signup "${J[@]}" -d "{\"email\":\"$EMAIL\",\"password\":\"$PW\",\"role\":\"CUSTOMER\"}"; err EMAIL_DUPLICATED
check "가입 ADMIN 거부" 400 POST /v1/auth/signup "${J[@]}" -d "{\"email\":\"adm_$EMAIL\",\"password\":\"$PW\",\"role\":\"ADMIN\"}"; err VALIDATION_ERROR
check "가입 잘못된 role" 400 POST /v1/auth/signup "${J[@]}" -d "{\"email\":\"x_$EMAIL\",\"password\":\"$PW\",\"role\":\"FOO\"}"; err VALIDATION_ERROR
check "가입 password 누락" 400 POST /v1/auth/signup "${J[@]}" -d "{\"email\":\"y_$EMAIL\",\"role\":\"CUSTOMER\"}"; err VALIDATION_ERROR

echo "--- 로그인"
check "로그인 비밀번호 틀림" 401 POST /v1/auth/login --data-urlencode "username=$EMAIL" --data-urlencode "password=wrong-pass"; err INVALID_CREDENTIALS
cp "$BODY" "$TMPD/login_wrong"
check "로그인 없는 사용자" 401 POST /v1/auth/login --data-urlencode "username=none_$EMAIL" --data-urlencode "password=$PW"; err INVALID_CREDENTIALS
if cmp -s "$BODY" "$TMPD/login_wrong"; then PASS=$((PASS+1)); echo "PASS    ↳ 실패 2종 본문 동일"; else FAIL=$((FAIL+1)); FAILED+=("로그인 실패 본문 동일"); echo "FAIL    ↳ 실패 2종 본문이 다름 (계정 존재 여부 노출)"; fi
check "로그인 password 누락" 400 POST /v1/auth/login --data-urlencode "username=$EMAIL"; err VALIDATION_ERROR
check "로그인 성공" 200 POST /v1/auth/login --data-urlencode "username=$EMAIL" --data-urlencode "password=$PW"
expect "  ↳ access_token, token_type=bearer" "d and d.get('access_token') and d.get('token_type')=='bearer'"
TOKEN="$(json "d.get('access_token','') if d else ''")"
A=(-H "Authorization: Bearer $TOKEN")

echo "--- 보호된 API"
check "토큰 없음" 401 GET /v1/users/me; err UNAUTHORIZED; bearer_header "토큰 없음"
check "위조 토큰" 401 GET /v1/users/me -H "Authorization: Bearer abc.def.ghi"; err UNAUTHORIZED; bearer_header "위조 토큰"
check "내 정보" 200 GET /v1/users/me "${A[@]}"
expect "  ↳ 가입한 이메일" "d and d.get('email')=='$EMAIL'"
check "포인트 내역" 200 GET "/v1/users/me/points?type=EARN&page=0&size=20" "${A[@]}"
check "포인트 type 잘못됨" 400 GET "/v1/users/me/points?type=FOO" "${A[@]}"; err VALIDATION_ERROR
check "포인트 size=101" 400 GET "/v1/users/me/points?size=101" "${A[@]}"; err VALIDATION_ERROR
check "포인트 page=-1" 400 GET "/v1/users/me/points?page=-1" "${A[@]}"; err VALIDATION_ERROR

echo "--- 로그아웃"
check "로그아웃 토큰 없음" 401 POST /v1/auth/logout; err UNAUTHORIZED
check "로그아웃" 204 POST /v1/auth/logout "${A[@]}"
check "로그아웃 후 재사용" 401 GET /v1/users/me "${A[@]}"; err TOKEN_REVOKED; bearer_header "로그아웃 후 재사용"
check "로그아웃 두 번" 401 POST /v1/auth/logout "${A[@]}"; err TOKEN_REVOKED

echo
echo "결과: PASS $PASS / FAIL $FAIL"
if [ "$FAIL" -gt 0 ]; then
  echo "실패 항목:"
  printf '  - %s\n' "${FAILED[@]}"
  exit 1
fi
