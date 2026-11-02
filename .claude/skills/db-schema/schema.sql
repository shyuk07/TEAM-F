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
    business_number  TEXT                                  -- 매장 운영자만 사용
);

CREATE TABLE point_log (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES users (id),
    amount      INTEGER     NOT NULL,                      -- 적립 +, 사용 -
    point_type  TEXT        NOT NULL CHECK (point_type IN ('EARN', 'USE', 'RESTORE', 'REVOKE')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX ix_point_log_user_id ON point_log (user_id);

CREATE TABLE token_blacklist (
    jti         TEXT        PRIMARY KEY,
    expires_at  TIMESTAMPTZ NOT NULL
);
CREATE INDEX ix_token_blacklist_expires_at ON token_blacklist (expires_at);

-- ── stores ────────────────────────────────────────────
CREATE TABLE stores (
    id               UUID             PRIMARY KEY DEFAULT gen_random_uuid(),
    owner_id         UUID             NOT NULL UNIQUE REFERENCES users (id),  -- 상점주 1인 1상점 (API 명세)
    name             VARCHAR(150)     NOT NULL,
    pickup_address   VARCHAR(500)     NOT NULL,
    latitude         DOUBLE PRECISION,
    longitude        DOUBLE PRECISION,
    created_at       TIMESTAMPTZ      NOT NULL DEFAULT now(),
    approval_at      TIMESTAMPTZ,                          -- 개설 시각 (API 명세). 원본 ERD는 VARCHAR(20)
    closed_at        TIMESTAMPTZ
);

-- ── catalog ───────────────────────────────────────────
CREATE TABLE products (
    id              UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id        UUID         NOT NULL REFERENCES stores (id),
    name            VARCHAR(200),
    category        VARCHAR(80),
    description     TEXT,
    original_price  INTEGER      CHECK (original_price >= 0),
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
    status           VARCHAR(20) NOT NULL CHECK (status IN ('SCHEDULED', 'ON_SALE', 'SOLD_OUT', 'CLOSED')),
    sales_start      TIMESTAMPTZ,
    is_active        BOOLEAN     NOT NULL DEFAULT TRUE,
    price            INTEGER,                              -- 확인 필요: sale_price와 중복
    CONSTRAINT ck_offer_remaining_stock CHECK (remaining_stock BETWEEN 0 AND initial_stock),
    CONSTRAINT ck_offer_pickup_window   CHECK (pickup_end > pickup_start)
);
CREATE INDEX ix_discount_offers_product_id ON discount_offers (product_id);

CREATE TABLE stock_log (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    offer_id    UUID        NOT NULL REFERENCES discount_offers (id),
    user_id     UUID        REFERENCES users (id),         -- 시스템 조정이면 NULL
    amount      INTEGER     NOT NULL,                      -- 차감 -, 복구 +
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
    price           INTEGER                                -- 확인 필요: unit_price/total_price와 중복
);
CREATE INDEX ix_pickup_reservations_user_id ON pickup_reservations (user_id);
CREATE INDEX ix_pickup_reservations_offer_id ON pickup_reservations (offer_id);

-- ── payments ──────────────────────────────────────────
CREATE TABLE payments (
    id                   UUID         PRIMARY KEY DEFAULT gen_random_uuid(),
    reservation_id       UUID         NOT NULL REFERENCES pickup_reservations (id),
    amount               INTEGER      CHECK (amount >= 0),
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
