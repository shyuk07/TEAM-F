// 실서버: 백엔드(E2E_BACKEND_URL, 격리 DB)를 띄우고 실행한다. 브라우저의 /v1 요청은 page.route로 그 백엔드에 전달한다.
// 필요한 환경변수: E2E_BACKEND_URL(예 http://localhost:8010), E2E_DATABASE_URL(시드 SQL용, 이름에 'e2e'가 있어야 함),
// E2E_BACKEND_PYTHON(백엔드 venv의 python 경로). 없으면 실행하지 않고 실패한다(skip으로 통과시키지 않음).
// 헬퍼는 e2e/reservations.spec.ts에서 복사했다(기존 spec 수정 금지).
import { execFileSync } from 'node:child_process';
import { expect, test, type APIRequestContext, type Page } from '@playwright/test';

const BACKEND = process.env.E2E_BACKEND_URL ?? '';
const DB_URL = process.env.E2E_DATABASE_URL ?? '';
const PYTHON = process.env.E2E_BACKEND_PYTHON ?? '';
const PASSWORD = 'password123';

function requireEnv() {
  if (!BACKEND || !DB_URL || !PYTHON) {
    throw new Error(
      'E2E_BACKEND_URL, E2E_DATABASE_URL, E2E_BACKEND_PYTHON이 필요합니다 (백엔드 필요)',
    );
  }
  if (!/e2e/.test(DB_URL)) throw new Error('E2E_DATABASE_URL은 격리된 e2e DB여야 합니다');
}

function runSql(sql: string, params: Record<string, string>): string {
  const code = [
    'import asyncio, json, os, sys',
    'from sqlalchemy import text',
    'from sqlalchemy.ext.asyncio import create_async_engine',
    'async def main():',
    '    e = create_async_engine(os.environ["E2E_DATABASE_URL"])',
    '    async with e.begin() as c:',
    '        r = await c.execute(text(sys.argv[1]), json.loads(sys.argv[2]))',
    '        row = r.first() if r.returns_rows else None',
    '    await e.dispose()',
    '    print("" if row is None else row[0])',
    'asyncio.run(main())',
  ].join('\n');
  return execFileSync(PYTHON, ['-c', code, sql, JSON.stringify(params)], { env: process.env })
    .toString()
    .trim();
}

function approveOwner(email: string) {
  runSql("UPDATE users SET status = 'APPROVED', approved_at = now() WHERE email = :e", {
    e: email.toLowerCase(),
  });
}

function insertStore(ownerEmail: string, tag: string): string {
  return runSql(
    'INSERT INTO stores (owner_id, name, pickup_address, latitude, longitude, approval_at) ' +
      'SELECT id, name, :addr, 37.556, 126.906, now() FROM users WHERE email = :e RETURNING id',
    { e: ownerEmail.toLowerCase(), addr: `서울특별시 마포구 망원로 ${tag}` },
  );
}

async function signup(api: APIRequestContext, email: string, role: 'CUSTOMER' | 'OWNER') {
  const res = await api.post(`${BACKEND}/v1/auth/signup`, {
    data: {
      email,
      password: PASSWORD,
      role,
      name: role === 'OWNER' ? '망원베이커리' : '고객',
      phone: '010-0000-0000',
    },
  });
  expect(res.status(), await res.text()).toBe(201);
  if (role === 'OWNER') approveOwner(email);
}

async function login(api: APIRequestContext, email: string) {
  const res = await api.post(`${BACKEND}/v1/auth/login`, { data: { email, password: PASSWORD } });
  expect(res.status(), await res.text()).toBe(200);
  return ((await res.json()) as { access_token: string }).access_token;
}

async function post(api: APIRequestContext, path: string, token: string, data: unknown) {
  const res = await api.post(`${BACKEND}${path}`, {
    data,
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(res.ok(), `${path}: ${res.status()} ${await res.text()}`).toBe(true);
  return (await res.json()) as { id: string };
}

/** 할인 1건(정가 6,000 → 3,000, 재고 10, 이미지 없음)과 예약이 없는 고객 계정을 만든다. */
async function seed(api: APIRequestContext) {
  const tag = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const ownerEmail = `owner${tag}@e2e.test`;
  const customerEmail = `customer${tag}@e2e.test`;
  await signup(api, ownerEmail, 'OWNER');
  const ownerToken = await login(api, ownerEmail);
  const storeId = insertStore(ownerEmail, tag);
  const productName = `E2E 소금빵 ${tag}`;
  const product = await post(api, `/v1/stores/${storeId}/products`, ownerToken, {
    name: productName,
    original_price: 6000,
  });
  const h = 3_600_000;
  const now = Date.now();
  const offer = await post(api, `/v1/products/${product.id}/offers`, ownerToken, {
    sale_price: 3000,
    initial_stock: 10,
    sales_end: new Date(now + 2 * h).toISOString(),
    pickup_start: new Date(now + 3 * h).toISOString(),
    pickup_end: new Date(now + 5 * h).toISOString(),
  });
  await signup(api, customerEmail, 'CUSTOMER');
  return { offerId: offer.id, productName, customerEmail };
}

async function forwardApi(page: Page) {
  await page.route(
    (url) => url.pathname.startsWith('/v1/'),
    async (route) => {
      const u = new URL(route.request().url());
      const response = await route.fetch({ url: `${BACKEND}${u.pathname}${u.search}` });
      await route.fulfill({ response });
    },
  );
}

/** 예약 생성 요청(POST /v1/reservations) 수를 센다. */
function countReservationPosts(page: Page) {
  const counter = { n: 0 };
  page.on('request', (r) => {
    if (r.method() === 'POST' && new URL(r.url()).pathname === '/v1/reservations') counter.n++;
  });
  return counter;
}

const stepper = (page: Page) => page.locator('.cta .step b');
const reserve = (page: Page) => page.getByRole('button', { name: /^예약하고 결제/ });

test.beforeAll(() => requireEnv());
// 테스트가 끝날 때 진행 중인 전달 요청이 「Test ended」로 실패하지 않게 한다.
test.afterEach(async ({ page }) => {
  await page.unrouteAll({ behavior: 'ignoreErrors' });
});

test('C2 → A1 → C2(qty 유지) → C3 → C2 결제 이어하기', async ({ page, request }) => {
  const { offerId, productName, customerEmail } = await seed(request);
  await forwardApi(page);
  const posts = countReservationPosts(page);

  // a. 비로그인 C2: 상품명·가격·픽업·취소 시한·이미지 대체, 탭 바 없음
  await page.goto(`/offers/${offerId}`);
  await expect(page.getByRole('heading', { level: 1, name: productName })).toBeVisible();
  await expect(page.getByText('3,000원', { exact: true })).toBeVisible();
  await expect(page.getByText('6,000', { exact: true })).toBeVisible();
  await expect(page.getByText('50%', { exact: true })).toBeVisible();
  await expect(page.getByText('픽업 시간', { exact: true })).toBeVisible();
  await expect(page.getByText(/^(오늘|내일|\d{2}\/\d{2}) \d{2}:\d{2}–\d{2}:\d{2}$/)).toBeVisible();
  await expect(page.getByText('취소 가능', { exact: true })).toBeVisible();
  await expect(page.getByText(/까지 \(이후 취소 불가\)$/)).toBeVisible();
  await expect(page.locator('.ph', { hasText: '상품 이미지' })).toBeVisible();
  await expect(page.getByRole('navigation', { name: '고객 메뉴' })).toHaveCount(0);

  // b. 수량 2 → 예약 → A1(from 유지) → 로그인 → C2?qty=2, 자동 예약 없음
  await page.getByRole('button', { name: '+' }).click();
  await expect(stepper(page)).toHaveText('2');
  await expect(reserve(page)).toHaveText('예약하고 결제 6,000원');
  await reserve(page).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByText('예약을 이어가려면 로그인하세요.')).toBeVisible();
  await page.getByLabel('이메일').fill(customerEmail);
  await page.getByLabel('비밀번호').fill(PASSWORD);
  await page.getByRole('button', { name: '로그인' }).click();
  await expect(page).toHaveURL(new RegExp(`/offers/${offerId}\\?qty=2$`));
  await expect(stepper(page)).toHaveText('2');
  await expect(reserve(page)).toHaveText('예약하고 결제 6,000원');
  await expect(reserve(page)).toBeEnabled();
  expect(posts.n).toBe(0);

  // c. 예약 → C3, 총액 2개 기준
  await reserve(page).click();
  await expect(page).toHaveURL(/\/checkout\/[0-9a-f-]{36}$/);
  const reservationId = new URL(page.url()).pathname.split('/').pop()!;
  await expect(page.getByRole('button', { name: '결제하기 6,000원' })).toBeVisible();
  expect(posts.n).toBe(1);

  // d. 같은 C2 재진입 → 예약 시도 시 409 → 「결제 이어하기」 → 같은 예약의 C3
  await page.goto(`/offers/${offerId}`);
  await expect(page.getByRole('heading', { level: 1, name: productName })).toBeVisible();
  await reserve(page).click();
  const cont = page.getByRole('button', { name: '결제 이어하기' });
  await expect(cont).toBeVisible();
  await cont.click();
  await expect(page).toHaveURL(new RegExp(`/checkout/${reservationId}$`));
});

test('C2 품절: 버튼 비활성, 사유 문구 정확히 1개', async ({ page, request }) => {
  const { offerId, productName } = await seed(request);
  runSql(
    "UPDATE discount_offers SET remaining_stock = 0, status = 'SOLD_OUT' WHERE id = CAST(:id AS uuid)",
    { id: offerId },
  );
  await forwardApi(page);
  await page.goto(`/offers/${offerId}`);
  await expect(page.getByRole('heading', { level: 1, name: productName })).toBeVisible();
  await expect(reserve(page)).toBeDisabled();
  await expect(page.getByText('품절됐어요.', { exact: true })).toHaveCount(1);
});

test('C2 없는 offerId: 없음 안내와 홈으로 링크', async ({ page }) => {
  await forwardApi(page);
  await page.goto('/offers/00000000-0000-0000-0000-000000000000');
  await expect(page.getByText('할인을 찾을 수 없어요.')).toBeVisible();
  await expect(page.getByRole('link', { name: '홈으로' })).toHaveAttribute('href', '/');
  await expect(reserve(page)).toHaveCount(0);
});
