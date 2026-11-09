-- 마감 직전(Last Call) PostgreSQL 스키마 (권장안)
-- 팀 ERD 원본을 PostgreSQL 문법에 맞게 고치고 FK·인덱스·기본값·CHECK를 더한 버전입니다.
-- "확인 필요" 주석이 붙은 항목은 팀 결정 후 확정합니다.
-- 검증: PostgreSQL 17(compose.yaml의 postgres:17)에서 이 파일 전체가 오류 없이 실행됨을 확인했습니다.
-- gen_random_uuid()는 PostgreSQL 13 이상에 기본 내장입니다.

-- ── auth ──────────────────────────────────────────────
CREATE TABLE users (
    id               UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    email            VARCHAR(255) NOT NULL UNIQUE,
    password_hash    VARCHAR(255) NOT NULL,
    role             VARCHAR(20)  NOT NULL,                -- 원본 `role/admin`. CUSTOMER, ADMIN, 상점주(값 이름 확인 필요)
    name             VARCHAR(100),
    phone            VARCHAR(100),
    users_point      INTEGER      NOT NULL DEFAULT 0 CHECK (users_point >= 0),
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    business_number  TEXT,                                 -- 매장 운영자만 사용
    -- 계정 상태 (docs/design/admin.md §2.1 S1~S5, D3·D4). 기존 행은 DEFAULT로 APPROVED
    status           VARCHAR(20)  NOT NULL DEFAULT 'APPROVED',
    approved_at      TIMESTAMPTZ,                          -- 상점주 승인 시각 (stores.approval_at과 별개, D6)
    rejected_reason  VARCHAR(500),
    rejected_at      TIMESTAMPTZ,
    suspended_reason VARCHAR(500),
    suspended_at     TIMESTAMPTZ,
    suspended_until  TIMESTAMPTZ,                          -- NULL이면 무기한 정지
    deleted_at       TIMESTAMPTZ,                          -- 강제 탈퇴(soft delete)
    deleted_reason   VARCHAR(500),
    -- 토큰 세대 (비밀번호 변경·재설정 시 기존 토큰 무효화, auth D-토큰무효화, S-A2)
    token_version    INTEGER      NOT NULL DEFAULT 0,
    token_keep_jti   TEXT,                                 -- 비밀번호 변경에 쓴 토큰 하나만 유지
    CONSTRAINT ck_users_status CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED', 'SUSPENDED', 'WITHDRAWN'))
);

CREATE TABLE point_log (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES users (id),
    amount      INTEGER     NOT NULL,                      -- 적립 +, 사용 -
    point_type  TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    reason         VARCHAR(500),                           -- 관리자 지급 사유. 시스템 이벤트는 NULL (admin.md S7)
    balance_after  INTEGER,                                -- 기록 직후 잔액. 이 컬럼 도입 전 행은 NULL (S8)
    created_by     UUID        REFERENCES users (id),      -- 지급한 관리자. 시스템 이벤트는 NULL (S9)
    CONSTRAINT ck_point_log_type CHECK (point_type IN ('EARN', 'USE', 'RESTORE', 'REVOKE', 'GRANT', 'EXPIRE'))  -- GRANT: 관리자 지급 (S6), EXPIRE: 탈퇴 소멸 (S-A1)
);
CREATE INDEX ix_point_log_user_id ON point_log (user_id);

CREATE TABLE token_blacklist (
    jti         TEXT        PRIMARY KEY,
    expires_at  TIMESTAMPTZ NOT NULL
);
CREATE INDEX ix_token_blacklist_expires_at ON token_blacklist (expires_at);

-- 비밀번호 재설정 코드: 회원당 1행, 원문 대신 해시 저장 (auth D-재설정코드, S-A3)
CREATE TABLE password_reset_codes (
    user_id          UUID         PRIMARY KEY REFERENCES users (id),
    code_hash        VARCHAR(255) NOT NULL,
    expires_at       TIMESTAMPTZ  NOT NULL,
    failed_attempts  INTEGER      NOT NULL DEFAULT 0 CONSTRAINT ck_password_reset_attempts_nonneg CHECK (failed_attempts >= 0),
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ── stores ────────────────────────────────────────────
CREATE TABLE stores (
    id               UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id         UUID             NOT NULL REFERENCES users (id),  -- 상점주 1인 1상점 (API 명세)
    name             VARCHAR(150)     NOT NULL,
    pickup_address   VARCHAR(500)     NOT NULL,
    latitude         DOUBLE PRECISION,
    longitude        DOUBLE PRECISION,
    created_at       TIMESTAMPTZ      NOT NULL DEFAULT now(),
    approval_at      TIMESTAMPTZ,                          -- 개설 시각 (API 명세). 원본 ERD는 VARCHAR(20)
    closed_at        TIMESTAMPTZ,
    -- 관리자 정지·폐점 (admin.md S10). 상태 컬럼 없이 closed_at > suspended_at > 영업 중으로 파생 (D16)
    suspended_reason VARCHAR(500),
    suspended_at     TIMESTAMPTZ,
    closed_reason    VARCHAR(500),
    CONSTRAINT uq_stores_owner_id UNIQUE (owner_id),
    -- 동일한 상점명과 주소의 상점 금지 (docs/design/stores.md D33). 폐점·정지 상점 포함
    CONSTRAINT uq_stores_name_address UNIQUE (name, pickup_address)
);

-- ── catalog ───────────────────────────────────────────
CREATE TABLE products (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id        UUID         NOT NULL REFERENCES stores (id),
    name            VARCHAR(200) NOT NULL,
    category        VARCHAR(80),
    description     TEXT,
    original_price  INTEGER      NOT NULL CHECK (original_price >= 0),
    is_active       BOOLEAN      NOT NULL DEFAULT TRUE,
    product_image   JSON
);
CREATE INDEX ix_products_store_id ON products (store_id);

CREATE TABLE discount_offers (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id       UUID        NOT NULL REFERENCES products (id),
    sale_price       INTEGER     NOT NULL CHECK (sale_price >= 0),
    initial_stock    INTEGER     NOT NULL CHECK (initial_stock >= 0),
    remaining_stock  INTEGER     NOT NULL,
    sales_end        TIMESTAMPTZ NOT NULL,
    pickup_start     TIMESTAMPTZ NOT NULL,
    pickup_end       TIMESTAMPTZ NOT NULL,
    status           VARCHAR(20) NOT NULL,
    sales_start      TIMESTAMPTZ NOT NULL,
    is_active        BOOLEAN     NOT NULL DEFAULT TRUE,
    price            INTEGER,                              -- 확인 필요: sale_price와 중복
    suspended_reason VARCHAR(500),                         -- 관리자 정지 (admin.md S11, D19)
    suspended_at     TIMESTAMPTZ,
    CONSTRAINT ck_offer_status CHECK (status IN ('SCHEDULED', 'ON_SALE', 'SOLD_OUT', 'CLOSED', 'SUSPENDED')),
    CONSTRAINT ck_offer_remaining_stock CHECK (remaining_stock BETWEEN 0 AND initial_stock),
    CONSTRAINT ck_offer_pickup_window   CHECK (pickup_end > pickup_start)
);
CREATE INDEX ix_discount_offers_product_id ON discount_offers (product_id);

CREATE TABLE stock_log (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    offer_id    UUID        NOT NULL REFERENCES discount_offers (id),
    user_id     UUID        REFERENCES users (id),         -- 시스템 조정이면 NULL
    amount      INTEGER     NOT NULL,                      -- 차감 -, 복구 +
    reason      VARCHAR(200),                              -- 조정 사유 (최초 입고는 '최초 입고')
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_stock_log_offer_id ON stock_log (offer_id);

-- ── reservations ──────────────────────────────────────
CREATE TABLE pickup_reservations (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID         NOT NULL REFERENCES users (id),
    offer_id        UUID         NOT NULL REFERENCES discount_offers (id),
    quantity        INTEGER      NOT NULL CHECK (quantity >= 1),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    total_price     INTEGER,
    status          VARCHAR(20),                           -- PENDING_PAYMENT, RESERVED(?), CANCELLED, PICKED_UP (확인 필요)
    unit_price      INTEGER,
    pickup_code     VARCHAR(20),
    cancelled_at    TIMESTAMPTZ,
    picked_up_at    TIMESTAMPTZ,
    store_name      VARCHAR(150),                          -- 예약 시점 스냅샷
    pickup_address  VARCHAR(500),                          -- 예약 시점 스냅샷
    product_name    VARCHAR(200),                          -- 예약 시점 스냅샷
    price           INTEGER,                               -- 확인 필요: unit_price/total_price와 중복
    cancelled_by    VARCHAR(20),                           -- 취소 주체. 기존 취소 행·미취소 행은 NULL (reservations.md 16.3)
    CONSTRAINT ck_reservation_cancelled_by CHECK (cancelled_by IN ('CUSTOMER', 'STORE', 'SYSTEM')),
    CONSTRAINT ck_reservation_cancelled_by_status CHECK (cancelled_by IS NULL OR status = 'CANCELLED')
);
CREATE INDEX ix_pickup_reservations_user_id ON pickup_reservations (user_id);
CREATE INDEX ix_pickup_reservations_offer_id ON pickup_reservations (offer_id);

-- ── payments ──────────────────────────────────────────
CREATE TABLE payments (
    id                   UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    reservation_id       UUID         NOT NULL REFERENCES pickup_reservations (id),
    amount               INTEGER      CHECK (amount >= 0),           -- 실제 결제 금액 = 예약 총액 - point_used
    point_used           INTEGER      NOT NULL DEFAULT 0 CHECK (point_used >= 0),  -- 결제에 사용한 포인트 (payments.md S-6)
    status               VARCHAR(30),                      -- READY, PAID, 실패 상태(확인 필요)
    provider_payment_id  VARCHAR(255),
    created_at           TIMESTAMPTZ  NOT NULL DEFAULT now(),
    paid_at              TIMESTAMPTZ,
    failed_at            TIMESTAMPTZ,
    failed_response      JSONB
);
CREATE INDEX ix_payments_reservation_id ON payments (reservation_id);

CREATE TABLE refunds (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_id      UUID         NOT NULL REFERENCES payments (id),
    refund_amount   INTEGER      CHECK (refund_amount >= 0),
    penalty_amount  INTEGER      CHECK (penalty_amount >= 0),
    reason          VARCHAR(200),
    status          VARCHAR(30),                           -- COMPLETED, 그 외(확인 필요)
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now(),
    completed_at    TIMESTAMPTZ,
    refund_reason   JSONB                                  -- 확인 필요: reason과 역할 구분
);
CREATE INDEX ix_refunds_payment_id ON refunds (payment_id);
