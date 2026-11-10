// 실서버: 백엔드(E2E_BACKEND_URL, 격리 DB)를 띄우고 실행한다. 브라우저의 /v1 요청은 page.route로 그 백엔드에 전달한다.
// 필요한 환경변수: E2E_BACKEND_URL(예 http://localhost:8010), E2E_DATABASE_URL(상점주 승인 SQL용, 이름에 'e2e'가 있어야 함),
// E2E_BACKEND_PYTHON(백엔드 venv의 python 경로). 없으면 실행하지 않고 실패한다(skip으로 통과시키지 않음).
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

/** 격리 e2e DB에서만 SQL을 실행하고 첫 행 첫 열을 문자열로 돌려준다(시드 전용). */
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

/** 상점주 승인 API가 없어 직접 UPDATE한다(backend/tests/helpers.py approve_owner와 같은 방식). */
function approveOwner(email: string) {
  runSql("UPDATE users SET status = 'APPROVED', approved_at = now() WHERE email = :e", {
    e: email.toLowerCase(),
  });
}

/** 상점 개설 API는 실제 지오코더(외부)를 불러 쓸 수 없어, 좌표를 고정값으로 넣은 상점 행을 직접 만든다. */
function insertStore(ownerEmail: string, tag: string): string {
  return runSql(
    'INSERT INTO stores (owner_id, name, pickup_address, latitude, longitude, approval_at) ' +
      'SELECT id, name, :addr, 37.556, 126.906, now() FROM users WHERE email = :e RETURNING id',
    { e: ownerEmail.toLowerCase(), addr: `서울특별시 마포구 망원로 ${tag}` },
  );
}

async function signupAndLogin(api: APIRequestContext, email: string, role: 'CUSTOMER' | 'OWNER') {
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
  const login = await api.post(`${BACKEND}/v1/auth/login`, { data: { email, password: PASSWORD } });
  expect(login.status(), await login.text()).toBe(200);
  return ((await login.json()) as { access_token: string }).access_token;
}

async function post(api: APIRequestContext, path: string, token: string, data: unknown) {
  const res = await api.post(`${BACKEND}${path}`, {
    data,
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(res.ok(), `${path}: ${res.status()} ${await res.text()}`).toBe(true);
  return (await res.json()) as { id: string };
}

/** 할인 1건과 그 할인에 대한 고객의 결제 대기 예약 1건을 만든다. */
async function seed(api: APIRequestContext) {
  const tag = `${Date.now()}${Math.floor(Math.random() * 1000)}`;
  const ownerEmail = `owner${tag}@e2e.test`;
  const customerEmail = `customer${tag}@e2e.test`;
  const ownerToken = await signupAndLogin(api, ownerEmail, 'OWNER');
  const storeId = insertStore(ownerEmail, tag);
  const product = await post(api, `/v1/stores/${storeId}/products`, ownerToken, {
    name: `E2E 식빵 ${tag}`,
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
  const customerToken = await signupAndLogin(api, customerEmail, 'CUSTOMER');
  const reservation = await post(api, '/v1/reservations', customerToken, {
    offer_id: offer.id,
    quantity: 1,
  });
  return { customerEmail, reservationId: reservation.id, productName: `E2E 식빵 ${tag}` };
}

/** 브라우저의 /v1 요청을 실제 백엔드로 넘긴다(vite proxy 대상 설정을 바꾸지 않기 위해). */
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

test.beforeAll(() => requireEnv());

test('C5: 비로그인으로 /me/reservations에 가면 /login으로 이동한다', async ({ page }) => {
  await forwardApi(page);
  await page.goto('/me/reservations');
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole('heading', { name: '로그인' })).toBeVisible();
});

test('A1 → C3 → C4 → C5 → C5a → C5b: 로그인·결제·픽업 코드·취소·지난 예약', async ({
  page,
  request,
}) => {
  const { customerEmail, reservationId, productName } = await seed(request);
  await forwardApi(page);

  // 비로그인으로 C3에 들어가면 로그인 뒤 같은 C3로 돌아온다(from 유지)
  await page.goto(`/checkout/${reservationId}`);
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel('이메일').fill(customerEmail);
  await page.getByLabel('비밀번호').fill(PASSWORD);
  await page.getByRole('button', { name: '로그인' }).click();
  await expect(page).toHaveURL(new RegExp(`/checkout/${reservationId}$`));

  // C3 결제(포인트 0)
  const pay = page.getByRole('button', { name: '결제하기 3,000원' });
  await expect(pay).toBeVisible();
  await pay.click();

  // C4 픽업 코드
  await expect(page).toHaveURL(new RegExp(`/checkout/${reservationId}/complete$`));
  await expect(page.getByText(/^[A-Z]\d{5}$/)).toBeVisible();
  await expect(page.getByText('매장에서 이 코드를 보여 주세요')).toBeVisible();
  await expect(page.getByText('예약 확정')).toBeVisible();

  // C5 진행 중 카드
  await page.getByText('내 예약 보기').click();
  await expect(page).toHaveURL(/\/me\/reservations$/);
  const card = page.locator('.box').filter({ hasText: productName }).first();
  await expect(card).toBeVisible();
  await expect(card.getByText('예약 확정')).toBeVisible();

  // C5a 취소 시트 → 취소
  await card.getByText(/^예약 취소 · \d{2}:\d{2}까지$/).click();
  await page.getByRole('button', { name: '예약 취소', exact: true }).click();
  await expect(page.getByText(productName)).toHaveCount(0);

  // C5b 지난 예약 탭에 취소됨
  await page.getByText('지난 예약', { exact: true }).click();
  await expect(page).toHaveURL(/\?tab=past$/);
  const pastCard = page.locator('.box').filter({ hasText: productName }).first();
  await expect(pastCard).toBeVisible();
  await expect(pastCard.getByText('취소됨')).toBeVisible();
});

// 리뷰 회귀: 긴 목록·모달·고객 외곽 폭은 고정 API 응답으로 브라우저 동작만 확인한다.
async function mockCustomerReservations(page: Page, pending = false) {
  const now = Date.now();
  const reservations = Array.from({ length: 15 }, (_, i) => ({
    id: `modal-r${i}`,
    offer_id: `modal-o${i}`,
    store_name: '검증 매장',
    product_name: `검증 상품 ${i}`,
    quantity: 1,
    total_price: 3000,
    status: pending ? 'PENDING_PAYMENT' : 'RESERVED',
    created_at: new Date(now - i * 1000).toISOString(),
    cancelled_by: null,
    pickup_code: 'A12345',
    pickup_address: '서울',
    pickup_start: new Date(now + 3 * 3_600_000).toISOString(),
    pickup_end: new Date(now + 5 * 3_600_000).toISOString(),
    cancellable_until: new Date(now + 2 * 3_600_000).toISOString(),
  }));
  await page.addInitScript(() => localStorage.setItem('lastcall.accessToken', 'modal-fixture'));
  await page.route('**/v1/**', async (route) => {
    const path = new URL(route.request().url()).pathname;
    const body =
      path === '/v1/users/me'
        ? {
            id: '00000000-0000-0000-0000-000000000001',
            email: 'modal@test.com',
            name: '고객',
            phone: null,
            role: 'CUSTOMER',
            users_point: 0,
            created_at: '2026-01-01T00:00:00Z',
            status: 'APPROVED',
          }
        : path.startsWith('/v1/reservations/')
          ? reservations[0]
          : { reservations, page: 1, size: 100, total: 15 };
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(body),
    });
  });
}

test('C5a: 긴 목록의 취소 시트는 화면 안에 보이고 배경 초점과 이동을 막는다', async ({ page }) => {
  await mockCustomerReservations(page);
  await page.goto('/me/reservations');
  const trigger = page.getByText(/^예약 취소 · /).first();
  await trigger.click();
  const dialog = page.getByRole('alertdialog');
  const bounds = await dialog.boundingBox();
  expect(bounds).not.toBeNull();
  expect.soft(bounds!.y).toBeGreaterThanOrEqual(0);
  expect.soft(bounds!.y + bounds!.height).toBeLessThanOrEqual(page.viewportSize()!.height);
  await expect.soft(dialog.getByRole('button', { name: '돌아가기' })).toBeFocused();
  const background = page.getByText('지난 예약', { exact: true });
  await background.evaluate((el) => (el as HTMLElement).focus());
  expect.soft(await dialog.evaluate((el) => el.contains(document.activeElement))).toBe(true);
  for (let i = 0; i < 4; i++) {
    await page.keyboard.press('Tab');
    expect.soft(await dialog.evaluate((el) => el.contains(document.activeElement))).toBe(true);
  }
  await dialog.getByRole('button', { name: '돌아가기' }).click();
  await expect(trigger).toBeFocused();
});

test('C3a: 결제 이탈 시트에서 배경 결제는 실행되지 않고 닫으면 뒤로 버튼으로 복귀한다', async ({
  page,
}) => {
  await mockCustomerReservations(page, true);
  let payments = 0;
  page.on('request', (request) => {
    if (new URL(request.url()).pathname === '/v1/payments') payments++;
  });
  await page.goto('/checkout/modal-r0');
  const pay = page.getByRole('button', { name: '결제하기 3,000원' });
  await expect(pay).toBeVisible();
  const payElement = await pay.elementHandle();
  await page.getByRole('button', { name: '뒤로', exact: true }).click();
  const dialog = page.getByRole('alertdialog');
  await expect.soft(dialog.getByRole('button', { name: '결제 계속하기' })).toBeFocused();
  await payElement!.evaluate((el) => (el as HTMLElement).focus());
  expect.soft(await dialog.evaluate((el) => el.contains(document.activeElement))).toBe(true);
  await page.keyboard.press('Enter');
  expect(payments).toBe(0);
  await expect(dialog).toBeHidden();
  await expect(page.getByRole('button', { name: '뒤로', exact: true })).toBeFocused();
});

test('고객 화면은 모바일 폭을 유지하고 PC 외곽 폭도 420px를 넘지 않는다', async ({ page }) => {
  await mockCustomerReservations(page);
  await page.goto('/me/reservations');
  await expect(page.getByText('검증 상품 0 × 1')).toBeVisible();
  const bounds = await page.locator('.app').boundingBox();
  const width = page.viewportSize()!.width;
  expect(bounds).not.toBeNull();
  expect(bounds!.width).toBe(Math.min(width, 420));
  expect(bounds!.x).toBe((width - bounds!.width) / 2);
});
