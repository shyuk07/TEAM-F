// 백엔드 응답은 page.route로 대체 (모킹)
import { expect, test, type Page } from '@playwright/test';
import { TOKEN_KEY, errorBody, json, mockOwnerSession, userDto } from './support/auth';

const token = (page: Page) => page.evaluate((k) => localStorage.getItem(k), TOKEN_KEY);

async function mockLogin(page: Page, role: 'OWNER' | 'CUSTOMER' = 'OWNER') {
  const meAuth: Array<string | undefined> = [];
  await page.route('**/v1/auth/login', (route) =>
    json(route, { access_token: 'tok1', token_type: 'bearer', status: 'APPROVED' }),
  );
  await page.route('**/v1/users/me', (route) => {
    meAuth.push(route.request().headers()['authorization']);
    return json(route, userDto(role));
  });
  return meAuth;
}

async function login(page: Page) {
  await page.getByLabel('이메일').fill('owner@test.com');
  await page.getByLabel('비밀번호').fill('pw1234');
  await page.getByRole('button', { name: '로그인' }).click();
}

test('A1: 비로그인 /owner/today는 /login으로 이동한다', async ({ page }) => {
  await page.goto('/owner/today');
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole('heading', { name: '로그인' })).toBeVisible();
});

test('A1 → O1: 로그인 성공 시 /owner/today, 토큰 저장, Bearer 헤더', async ({ page }) => {
  const meAuth = await mockLogin(page);
  await page.goto('/login');
  await login(page);
  await expect(page).toHaveURL(/\/owner\/today$/);
  await expect(page.getByRole('heading', { name: 'O1 오늘' })).toBeVisible();
  expect(await token(page)).toBe('tok1');
  expect(meAuth.length).toBeGreaterThan(0);
  expect(meAuth[meAuth.length - 1]).toBe('Bearer tok1');
});

test('O2 → A1 → O2: 비로그인 /owner/offers는 로그인 뒤 원래 화면으로 돌아온다', async ({
  page,
}) => {
  await mockLogin(page);
  await page.goto('/owner/offers');
  await expect(page).toHaveURL(/\/login$/);
  await login(page);
  await expect(page).toHaveURL(/\/owner\/offers$/);
  await expect(page.getByRole('heading', { name: 'O2 할인' })).toBeVisible();
});

test('A1: 로그인 실패(401)는 문구를 보이고 /login에 머문다', async ({ page }) => {
  await page.route('**/v1/auth/login', (route) =>
    route.fulfill(errorBody(401, 'INVALID_CREDENTIALS', '서버 문구')),
  );
  await page.goto('/login');
  await login(page);
  await expect(page.getByText('이메일 또는 비밀번호가 올바르지 않습니다.')).toBeVisible();
  await expect(page).toHaveURL(/\/login$/);
  expect(await token(page)).toBeNull();
});

test('O1: 로그인한 채 새로고침하면 같은 화면이고 /users/me를 다시 확인한다', async ({ page }) => {
  await mockOwnerSession(page);
  let meCalls = 0;
  await page.route('**/v1/users/me', (route) => {
    meCalls += 1;
    return json(route, userDto('OWNER'));
  });
  await page.goto('/owner/today');
  await expect(page.getByRole('heading', { name: 'O1 오늘' })).toBeVisible();
  const before = meCalls;
  await page.reload();
  await expect(page).toHaveURL(/\/owner\/today$/);
  await expect(page.getByRole('heading', { name: 'O1 오늘' })).toBeVisible();
  expect(meCalls).toBeGreaterThan(before);
});

test('O1 → A1: /users/me가 401 TOKEN_REVOKED면 /login으로 가고 토큰이 지워진다', async ({
  page,
}) => {
  await page.addInitScript((k) => localStorage.setItem(k, 'old'), TOKEN_KEY);
  await page.route('**/v1/users/me', (route) =>
    route.fulfill(errorBody(401, 'TOKEN_REVOKED', '폐기된 토큰입니다.')),
  );
  await page.goto('/owner/today');
  await expect(page).toHaveURL(/\/login$/);
  expect(await token(page)).toBeNull();
});

test('O8·C10: 계정 메뉴 → 로그아웃 취소 → 확인하면 /login, 토큰 삭제', async ({ page }) => {
  await mockOwnerSession(page);
  let logoutCalls = 0;
  await page.route('**/v1/auth/logout', (route) => {
    logoutCalls += 1;
    return route.fulfill({ status: 204 });
  });
  await page.goto('/owner/today');
  const open = () => page.getByRole('button', { name: '계정' }).click();

  await open();
  const menu = page.getByRole('dialog', { name: '계정 메뉴' });
  await expect(menu).toBeVisible();
  expect(await menu.evaluate((el) => el.closest('.app') !== null)).toBe(true);
  await menu.getByRole('button', { name: '로그아웃' }).click();
  const confirm = page.getByRole('alertdialog');
  await expect(confirm.getByText('로그아웃할까요?')).toBeVisible();
  expect(await confirm.evaluate((el) => el.closest('.app') !== null)).toBe(true);
  await confirm.getByRole('button', { name: '취소' }).click();
  await expect(confirm).toHaveCount(0);
  expect(logoutCalls).toBe(0);
  await expect(page).toHaveURL(/\/owner\/today$/);

  await open();
  await page
    .getByRole('dialog', { name: '계정 메뉴' })
    .getByRole('button', { name: '로그아웃' })
    .click();
  await page.getByRole('alertdialog').getByRole('button', { name: '로그아웃' }).click();
  await expect(page).toHaveURL(/\/login$/);
  expect(logoutCalls).toBe(1);
  expect(await token(page)).toBeNull();

  await page.goto('/owner/today');
  await expect(page).toHaveURL(/\/login$/);
});

test('A1 → C1: CUSTOMER 계정으로 로그인하면 /로 이동한다', async ({ page }) => {
  await mockLogin(page, 'CUSTOMER');
  await page.goto('/login');
  await login(page);
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('heading', { name: '마감 직전' })).toBeVisible();
});
