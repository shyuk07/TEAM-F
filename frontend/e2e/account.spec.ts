// 백엔드 응답은 page.route로 대체 (모킹)
import { expect, test, type Page } from '@playwright/test';
import {
  TOKEN_KEY,
  errorBody,
  json,
  mockOwnerSession,
  mockOwnerSessionWithProfile,
  userDto,
} from './support/auth';

const token = (page: Page) => page.evaluate((k) => localStorage.getItem(k), TOKEN_KEY);

// 주 버튼은 .cta(모바일)와 .dk(720px 이상) 두 벌이다. 지금 뷰포트에서 보이는 것을 누른다.
function visibleButton(page: Page, name: string) {
  return page.getByRole('button', { name }).filter({ visible: true }).first();
}

// 가입 → 로그인 → /users/me 흐름을 모킹하고 가입 요청 본문을 모은다.
async function mockSignupFlow(page: Page, role: 'OWNER' | 'CUSTOMER') {
  const signupBodies: unknown[] = [];
  await page.route('**/v1/auth/signup', (route) => {
    signupBodies.push(route.request().postDataJSON());
    return json(route, userDto(role), 201);
  });
  await page.route('**/v1/auth/login', (route) =>
    json(route, { access_token: 'tok1', token_type: 'bearer', status: 'APPROVED' }),
  );
  await page.route('**/v1/users/me', (route) => json(route, userDto(role)));
  return signupBodies;
}

async function fillSignup(page: Page, nameLabel: string) {
  await page.getByLabel(nameLabel, { exact: true }).fill('홍길동');
  await page.getByLabel('이메일 *', { exact: true }).fill('new@test.com');
  await page.getByLabel('비밀번호 * (8자 이상)', { exact: true }).fill('pw123456');
  await page.getByLabel('전화번호 *', { exact: true }).fill('010-1234-5678');
}

async function openAccountMenu(page: Page) {
  await page.goto('/owner/today');
  await expect(page.getByRole('heading', { name: 'O1 오늘' })).toBeVisible();
  await page.getByRole('button', { name: '계정' }).click();
  return page.getByRole('dialog', { name: '계정 메뉴' });
}

test('A1 → A2 → C1: 고객으로 가입하면 로그인되어 /로 이동한다', async ({ page }) => {
  const bodies = await mockSignupFlow(page, 'CUSTOMER');
  await page.goto('/login');
  await page.getByRole('link', { name: '회원가입' }).click();
  await expect(page).toHaveURL(/\/signup$/);
  await fillSignup(page, '이름 *');
  await visibleButton(page, '가입하기').click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('heading', { name: '마감 직전' })).toBeVisible();
  expect(bodies).toHaveLength(1);
  expect(bodies[0]).toMatchObject({ role: 'CUSTOMER', email: 'new@test.com' });
});

test('A1 → A2(상점주) → O1: 입점 신청으로 들어오면 상점주가 선택되고 가입 뒤 /owner/today', async ({
  page,
}) => {
  const bodies = await mockSignupFlow(page, 'OWNER');
  await page.goto('/login');
  await page.getByRole('link', { name: '사장님이신가요? 입점 신청' }).click();
  await expect(page).toHaveURL(/\/signup\?role=owner$/);
  await expect(page.getByRole('radio', { name: /^상점주/ })).toHaveAttribute(
    'aria-checked',
    'true',
  );
  await expect(page.getByLabel('상호(상점명으로 쓰임) *', { exact: true })).toBeVisible();
  await fillSignup(page, '상호(상점명으로 쓰임) *');
  await visibleButton(page, '가입하기').click();
  await expect(page).toHaveURL(/\/owner\/today$/);
  expect(bodies[0]).toMatchObject({ role: 'OWNER' });
});

test('A2: 409 EMAIL_DUPLICATED면 문구를 보이고 /signup에 머문다', async ({ page }) => {
  await page.route('**/v1/auth/signup', (route) =>
    route.fulfill(errorBody(409, 'EMAIL_DUPLICATED', '이미 가입된 이메일입니다.')),
  );
  await page.goto('/signup');
  await fillSignup(page, '이름 *');
  await visibleButton(page, '가입하기').click();
  await expect(page.getByText('이미 가입된 이메일입니다.')).toBeVisible();
  await expect(page).toHaveURL(/\/signup$/);
});

test('A1 → A3 → A1: 코드를 받아 비밀번호를 바꾸면 /login에 안내가 보이고 토큰이 없다', async ({
  page,
}) => {
  const confirmBodies: unknown[] = [];
  await page.route('**/v1/auth/password-reset/request', (route) => route.fulfill({ status: 204 }));
  await page.route('**/v1/auth/password-reset/confirm', (route) => {
    confirmBodies.push(route.request().postDataJSON());
    return route.fulfill({ status: 204 });
  });
  await page.goto('/login');
  await page.getByRole('link', { name: '비밀번호 재설정' }).click();
  await expect(page).toHaveURL(/\/password-reset$/);
  await page.getByLabel('가입한 이메일', { exact: true }).fill('owner@test.com');
  await page.getByRole('button', { name: '코드 보내기' }).click();
  await page.getByLabel('6자리 코드', { exact: true }).fill('123456');
  await page.getByLabel('새 비밀번호 (8자 이상)', { exact: true }).fill('newpw1234');
  await visibleButton(page, '비밀번호 바꾸기').click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole('status')).toHaveText('새 비밀번호로 로그인하세요');
  expect(confirmBodies[0]).toEqual({
    email: 'owner@test.com',
    code: '123456',
    new_password: 'newpw1234',
  });
  expect(await token(page)).toBeNull();
});

test('A3: 확인이 400 INVALID_RESET_CODE면 화면 문구를 보인다', async ({ page }) => {
  await page.route('**/v1/auth/password-reset/request', (route) => route.fulfill({ status: 204 }));
  await page.route('**/v1/auth/password-reset/confirm', (route) =>
    route.fulfill(
      errorBody(400, 'INVALID_RESET_CODE', '재설정 코드가 올바르지 않거나 만료되었습니다.'),
    ),
  );
  await page.goto('/password-reset');
  await page.getByLabel('가입한 이메일', { exact: true }).fill('owner@test.com');
  await page.getByRole('button', { name: '코드 보내기' }).click();
  await page.getByLabel('6자리 코드', { exact: true }).fill('000000');
  await page.getByLabel('새 비밀번호 (8자 이상)', { exact: true }).fill('newpw1234');
  await visibleButton(page, '비밀번호 바꾸기').click();
  await expect(
    page.getByText('코드가 맞지 않거나 만료됐어요. 코드를 다시 받아 주세요.'),
  ).toBeVisible();
  await expect(page).toHaveURL(/\/password-reset$/);
});

test('O1 → O8 → C8 → O1: 상호는 잠겨 있고 전화번호만 저장한 뒤 뒤로 돌아간다', async ({ page }) => {
  const { patches } = await mockOwnerSessionWithProfile(page);
  const menu = await openAccountMenu(page);
  await menu.getByRole('link', { name: /^내 정보 \(전화번호\)/ }).click();
  await expect(page).toHaveURL(/\/account\/profile$/);
  await expect(page.getByRole('heading', { name: '프로필 변경' })).toBeVisible();
  const shop = page.getByLabel('상호 (변경 불가)', { exact: true });
  await expect(shop).toHaveAttribute('readonly', '');
  await expect(shop).toHaveValue('김사장');
  await page.getByLabel('전화번호', { exact: true }).fill('010-2222-3333');
  await visibleButton(page, '저장').click();
  await expect(page.getByRole('status')).toHaveText('저장했어요');
  expect(patches).toEqual([{ phone: '010-2222-3333' }]);
  await page.getByRole('link', { name: '뒤로' }).click();
  await expect(page).toHaveURL(/\/owner\/today$/);
});

test('O8 → C9: 비밀번호를 바꾸면 완료 문구가 보이고 토큰과 URL이 그대로다', async ({ page }) => {
  await mockOwnerSession(page);
  const bodies: unknown[] = [];
  await page.route('**/v1/users/me/password', (route) => {
    bodies.push(route.request().postDataJSON());
    return route.fulfill({ status: 204 });
  });
  const menu = await openAccountMenu(page);
  await menu.getByRole('link', { name: /^비밀번호 변경/ }).click();
  await expect(page).toHaveURL(/\/account\/password$/);
  await page.getByLabel('현재 비밀번호', { exact: true }).fill('old12345');
  await page.getByLabel('새 비밀번호 (8자 이상)', { exact: true }).fill('new12345');
  await page.getByLabel('새 비밀번호 확인', { exact: true }).fill('new12345');
  await visibleButton(page, '비밀번호 바꾸기').click();
  await expect(page.getByRole('status')).toHaveText('비밀번호를 바꿨어요.');
  expect(bodies).toEqual([{ current_password: 'old12345', new_password: 'new12345' }]);
  expect(await token(page)).toBe('t');
  await expect(page).toHaveURL(/\/account\/password$/);
});

test('A1: 429 ACCOUNT_LOCKED(Retry-After 540)면 서버 문구를 그대로 보인다', async ({ page }) => {
  const message = '로그인 시도가 너무 많아 계정이 잠겼습니다. 9분 뒤에 다시 시도해 주세요.';
  await page.route('**/v1/auth/login', (route) =>
    route.fulfill({
      ...errorBody(429, 'ACCOUNT_LOCKED', message),
      headers: { 'Retry-After': '540' },
    }),
  );
  await page.goto('/login');
  await page.getByLabel('이메일').fill('owner@test.com');
  await page.getByLabel('비밀번호').fill('pw1234');
  await page.getByRole('button', { name: '로그인' }).click();
  await expect(page.getByRole('alert')).toHaveText(message);
  await expect(page).toHaveURL(/\/login$/);
});

test('C8: 「저장」은 뷰포트에 맞는 한 벌만 보인다(mobile .cta, desktop .dk)', async ({
  page,
}, testInfo) => {
  await mockOwnerSessionWithProfile(page);
  await page.goto('/account/profile');
  await expect(page.getByRole('heading', { name: '프로필 변경' })).toBeVisible();
  const visible = page.getByRole('button', { name: '저장' }).filter({ visible: true });
  await expect(visible).toHaveCount(1);
  const inCta = await visible.evaluate((el) => el.closest('.cta') !== null);
  const isDk = await visible.evaluate((el) => el.classList.contains('dk'));
  if (testInfo.project.name === 'mobile') {
    expect(inCta).toBe(true);
    expect(isDk).toBe(false);
  } else {
    expect(isDk).toBe(true);
    expect(inCta).toBe(false);
  }
});
