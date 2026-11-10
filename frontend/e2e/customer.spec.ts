// 고객 셸·C1·C6·C7·C10·C11 흐름 (customer-home.md §8(e)). 백엔드 응답은 page.route로 대체 (모킹)
import { expect, test, type Page, type Route } from '@playwright/test';
import { TOKEN_KEY, errorBody, json, mockCustomerSession, userDto } from './support/auth';

// 표시 시각은 브라우저 로컬 기준(customer-home.md D-13). 한국 시각으로 고정한다.
test.use({ timezoneId: 'Asia/Seoul' });

const NOW = new Date('2026-11-10T17:18:00+09:00');

const token = (page: Page) => page.evaluate((k) => localStorage.getItem(k), TOKEN_KEY);

// 주 버튼이 .cta·.dk 두 벌인 화면이 있어 지금 뷰포트에서 보이는 것을 누른다.
function visibleButton(page: Page, name: string) {
  return page.getByRole('button', { name }).filter({ visible: true }).first();
}

const offerDto = {
  id: 'o1',
  product_id: 'p1',
  store_id: 's1',
  store_name: '망원베이커리',
  product_name: '소금빵 세트',
  original_price: 12000,
  sale_price: 6000,
  discount_rate: 50,
  initial_stock: 10,
  remaining_stock: 3,
  is_sold_out: false,
  sales_start: '2026-11-10T15:00:00+09:00',
  sales_end: '2026-11-10T18:00:00+09:00',
  pickup_start: '2026-11-10T18:00:00+09:00',
  pickup_end: '2026-11-10T20:00:00+09:00',
  status: 'ON_SALE',
  is_active: true,
};

// GET /v1/offers: 받은 요청 URL을 모으고, 위치가 없으면 distance null
async function mockOffers(page: Page) {
  const requests: URL[] = [];
  await page.route(
    (url) => url.pathname === '/v1/offers',
    (route) => {
      const url = new URL(route.request().url());
      requests.push(url);
      const distance = url.searchParams.has('lat') ? 0.42 : null;
      return json(route, {
        items: [{ offer: offerDto, distance, unit: 'km' }],
        page: 1,
        size: 20,
        total: 1,
      });
    },
  );
  return requests;
}

function pointLog(i: number, amount = 115, type = 'EARN') {
  return {
    id: `pl${i}`,
    amount,
    point_type: type,
    balance_after: 1240,
    created_at: '2026-11-07T18:02:00+09:00',
  };
}

// GET /v1/users/me/points: size 3(C6)은 3행, size 20(C11)은 total 25로 0·1페이지
async function mockPoints(page: Page) {
  const requests: URL[] = [];
  await page.route(
    (url) => url.pathname === '/v1/users/me/points',
    (route) => {
      const url = new URL(route.request().url());
      requests.push(url);
      const p = Number(url.searchParams.get('page'));
      const size = Number(url.searchParams.get('size'));
      if (size <= 3) {
        const logs = [pointLog(1), pointLog(2, -500, 'USE'), pointLog(3, 1000, 'GRANT')];
        return json(route, { users_point: 1240, logs, page: p, size, total_elements: 3 });
      }
      const count = p === 0 ? 20 : 5;
      const logs = Array.from({ length: count }, (_, i) => pointLog(p * 20 + i + 1));
      return json(route, { users_point: 1240, logs, page: p, size, total_elements: 25 });
    },
  );
  return requests;
}

async function mockLogin(page: Page) {
  await page.route('**/v1/auth/login', (route) =>
    json(route, { access_token: 'tok1', token_type: 'bearer', status: 'APPROVED' }),
  );
  await page.route('**/v1/users/me', (route) => json(route, userDto('CUSTOMER')));
}

async function fillLogin(page: Page) {
  await page.getByLabel('이메일').fill('customer@test.com');
  await page.getByLabel('비밀번호').fill('pw123456');
  await page.getByRole('button', { name: '로그인' }).click();
}

// 위치 권한 거부: getCurrentPosition이 바로 오류 콜백을 부른다.
async function denyGeolocation(page: Page) {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, 'geolocation', {
      configurable: true,
      value: {
        getCurrentPosition: (...args: [unknown, (e: { code: number; message: string }) => void]) =>
          args[1]({ code: 1, message: 'denied' }),
      },
    });
  });
}

test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(NOW);
});

test('C1 비로그인(위치 없음): 거리 없음·가까운 순 비활성·카운트다운 → C2 자리 → ← 홈 → 입점 신청', async ({
  page,
}) => {
  await denyGeolocation(page);
  const offerRequests = await mockOffers(page);
  await page.goto('/');
  await expect(page.getByRole('heading', { name: '마감직전' })).toBeVisible();
  const card = page.getByRole('link', { name: /소금빵 세트/ });
  await expect(card).toBeVisible();
  await expect(card).toContainText('망원베이커리');
  await expect(card).not.toContainText('망원베이커리 ·');
  await expect(card).toContainText('판매 마감 42분 전');
  await expect(page.getByRole('button', { name: '가까운 순' })).toHaveAttribute(
    'aria-disabled',
    'true',
  );
  expect(offerRequests.length).toBeGreaterThan(0);
  expect(offerRequests.at(-1)?.searchParams.has('lat')).toBe(false);

  await card.click();
  await expect(page).toHaveURL(/\/offers\/o1$/);
  await expect(page.getByRole('heading', { name: 'C2 할인 상세' })).toBeVisible();
  await page.getByRole('link', { name: '뒤로' }).click();
  await expect(page).toHaveURL(/\/$/);

  await page.getByRole('link', { name: '사장님이신가요? 입점 신청' }).click();
  await expect(page).toHaveURL(/\/signup\?role=owner$/);
  await expect(page.getByRole('radio', { name: /^상점주/ })).toHaveAttribute(
    'aria-checked',
    'true',
  );
});

test('비로그인 「마이」 탭 → A1 안내 → 고객 로그인 → C6(잔액·최근 3행) → C11 「더 보기」(page=1)', async ({
  page,
}) => {
  await denyGeolocation(page);
  await mockOffers(page);
  const pointRequests = await mockPoints(page);
  await mockLogin(page);
  await page.goto('/');
  await page
    .getByRole('navigation', { name: '고객 메뉴' })
    .getByRole('link', { name: '마이' })
    .click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByText('예약 내역을 보려면 로그인하세요.')).toBeVisible();

  await fillLogin(page);
  await expect(page).toHaveURL(/\/me$/);
  await expect(page.getByRole('heading', { name: '마이' })).toBeVisible();
  await expect(page.getByText('1,240P', { exact: true })).toBeVisible();
  await expect(page.getByText('+115P')).toBeVisible();
  await expect(page.getByText('−500P')).toBeVisible();
  await expect(page.getByText('+1,000P')).toBeVisible();

  await page.getByRole('link', { name: '전체 보기' }).click();
  await expect(page).toHaveURL(/\/me\/points$/);
  await expect(page.getByRole('heading', { name: '포인트' })).toBeVisible();
  await page.getByRole('button', { name: '더 보기' }).click();
  await expect(page.getByRole('button', { name: '더 보기' })).toHaveCount(0);
  expect(
    pointRequests.some(
      (u) => u.searchParams.get('page') === '1' && u.searchParams.get('size') === '20',
    ),
  ).toBe(true);
});

test('고객 C6 → C10 로그아웃 → C1, 다시 로그인 → C7 400 문구 → 200 → C1·토큰 없음', async ({
  page,
}) => {
  await denyGeolocation(page);
  await mockCustomerSession(page);
  await mockOffers(page);
  await mockPoints(page);
  let logoutCalls = 0;
  await page.route('**/v1/auth/logout', (route: Route) => {
    logoutCalls += 1;
    return route.fulfill({ status: 204 });
  });
  const withdrawBodies: unknown[] = [];
  await page.route('**/v1/users/me/withdraw', (route) => {
    withdrawBodies.push(route.request().postDataJSON());
    if (withdrawBodies.length === 1) {
      return route.fulfill(
        errorBody(400, 'CURRENT_PASSWORD_MISMATCH', '현재 비밀번호가 올바르지 않습니다.'),
      );
    }
    return json(route, {
      id: '00000000-0000-0000-0000-000000000001',
      status: 'WITHDRAWN',
      deleted_at: '2026-11-10T08:18:00Z',
      cancelled_reservation_count: 0,
    });
  });

  await page.goto('/me');
  await expect(page.getByRole('heading', { name: '마이' })).toBeVisible();
  await page.getByRole('button', { name: /로그아웃/ }).click();
  const sheet = page.getByRole('alertdialog', { name: '로그아웃할까요?' });
  await expect(sheet).toBeVisible();
  await expect(
    sheet.getByText('진행 중인 예약은 그대로 남아요. 다시 로그인하면 볼 수 있어요.'),
  ).toBeVisible();
  await sheet.getByRole('button', { name: '로그아웃' }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole('link', { name: '로그인' })).toBeVisible();
  expect(logoutCalls).toBe(1);

  await page.route('**/v1/auth/login', (route) =>
    json(route, { access_token: 'tok1', token_type: 'bearer', status: 'APPROVED' }),
  );
  await page.getByRole('link', { name: '로그인' }).click();
  await fillLogin(page);
  await expect(page).toHaveURL(/\/$/);

  await page.goto('/me/withdraw');
  await expect(page.getByRole('heading', { name: '회원 탈퇴' })).toBeVisible();
  await page.getByLabel('현재 비밀번호 *', { exact: true }).fill('wrong-pw');
  await visibleButton(page, '탈퇴하기').click();
  await expect(page.getByText('비밀번호가 일치하지 않습니다.')).toBeVisible();
  await page.getByLabel('현재 비밀번호 *', { exact: true }).fill('pw123456');
  await visibleButton(page, '탈퇴하기').click();
  await expect(page).toHaveURL(/\/$/);
  expect(withdrawBodies).toEqual([{ password: 'wrong-pw' }, { password: 'pw123456' }]);
  expect(await token(page)).toBeNull();
});
