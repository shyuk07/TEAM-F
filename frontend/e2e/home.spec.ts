// 백엔드 응답은 page.route로 대체 (모킹). 위치는 Playwright geolocation 권한으로 만든다.
import { expect, test, type Page } from '@playwright/test';
import { errorBody, json, userDto } from './support/auth';

const SEOUL = { latitude: 37.5, longitude: 126.9 };

function offerDto(overrides: Record<string, unknown> = {}) {
  const inMinutes = (m: number) => new Date(Date.now() + m * 60_000).toISOString();
  return {
    id: '11111111-1111-4111-8111-111111111111',
    product_id: '22222222-2222-4222-8222-222222222222',
    store_id: '33333333-3333-4333-8333-333333333333',
    store_name: '망원베이커리',
    product_name: '식빵 모둠 5종',
    original_price: 12000,
    sale_price: 6000,
    discount_rate: 50,
    initial_stock: 10,
    remaining_stock: 3,
    is_sold_out: false,
    sales_start: inMinutes(-60),
    sales_end: inMinutes(42),
    pickup_start: inMinutes(60),
    pickup_end: inMinutes(180),
    status: 'ON_SALE',
    is_active: true,
    ...overrides,
  };
}

function listBody(distance: number | null = 0.4) {
  return { items: [{ offer: offerDto(), distance, unit: 'km' }], page: 1, size: 20, total: 1 };
}

// 요청 URL을 기록하고 목록을 돌려준다.
async function mockOffers(page: Page, distance: number | null = 0.4) {
  const urls: URL[] = [];
  await page.route('**/v1/offers**', (route) => {
    urls.push(new URL(route.request().url()));
    return json(route, listBody(distance));
  });
  return urls;
}

test.describe('위치 허용', () => {
  test.use({ permissions: ['geolocation'], geolocation: SEOUL });

  test('C1: 위치 허용 → 요청에 lat·lng·radius_km=3, 카드와 거리가 보인다', async ({ page }) => {
    const urls = await mockOffers(page);
    await page.goto('/');
    await expect(page.getByText('식빵 모둠 5종')).toBeVisible();
    await expect(page.getByText('망원베이커리 · 0.4km')).toBeVisible();
    await expect(page.getByText('내 주변 · 3km')).toBeVisible();
    const last = urls.at(-1);
    expect(Number(last?.searchParams.get('lat'))).toBeCloseTo(37.5);
    expect(Number(last?.searchParams.get('lng'))).toBeCloseTo(126.9);
    expect(last?.searchParams.get('radius_km')).toBe('3');
  });

  test('C1: 「할인율」 칩을 누르면 sort=discount_rate로 요청한다', async ({ page }) => {
    const urls = await mockOffers(page);
    await page.goto('/');
    await expect(page.getByText('식빵 모둠 5종')).toBeVisible();
    await page.getByRole('button', { name: '할인율' }).click();
    await expect.poll(() => urls.at(-1)?.searchParams.get('sort')).toBe('discount_rate');
  });

  test('C1: 검색어를 입력하고 Enter를 누르면 keyword로 요청한다', async ({ page }) => {
    const urls = await mockOffers(page);
    await page.goto('/');
    await expect(page.getByText('식빵 모둠 5종')).toBeVisible();
    await page.getByLabel('상품명 검색').fill('빵');
    await page.getByLabel('상품명 검색').press('Enter');
    await expect.poll(() => urls.at(-1)?.searchParams.get('keyword')).toBe('빵');
  });

  test('C1: 응답 500이면 오류 문구가 나오고 「다시 시도」로 목록을 다시 불러온다', async ({
    page,
  }) => {
    let fail = true;
    await page.route('**/v1/offers**', (route) =>
      fail ? route.fulfill(errorBody(500, 'INTERNAL_ERROR', '서버 오류')) : json(route, listBody()),
    );
    await page.goto('/');
    await expect(
      page.getByText('할인 목록을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.'),
    ).toBeVisible();
    fail = false;
    await page.getByRole('button', { name: '다시 시도' }).click();
    await expect(page.getByText('식빵 모둠 5종')).toBeVisible();
  });
});

test.describe('위치 거부', () => {
  test.use({ permissions: [] });

  test('C1: 위치 거부 → 요청에 lat이 없고 거리가 없으며 「가까운 순」이 비활성이다', async ({
    page,
  }) => {
    const urls = await mockOffers(page, null);
    await page.goto('/');
    await expect(page.getByText('식빵 모둠 5종')).toBeVisible();
    await expect(page.getByText('위치 없음')).toBeVisible();
    await expect(page.getByRole('button', { name: '가까운 순' })).toBeDisabled();
    await expect(page.getByText(/km/)).toHaveCount(0);
    expect(urls.length).toBeGreaterThan(0);
    for (const url of urls) {
      expect(url.searchParams.has('lat')).toBe(false);
      expect(url.searchParams.has('lng')).toBe(false);
      expect(url.searchParams.has('radius_km')).toBe(false);
    }
  });
});

test.describe('C1a 위치 · 반경', () => {
  test.describe('위치 허용', () => {
    test.use({ permissions: ['geolocation'], geolocation: SEOUL });

    test('C1a: 5km 선택은 적용 전 요청하지 않고, 「적용」하면 radius_km=5로 요청한다', async ({
      page,
    }) => {
      const urls = await mockOffers(page);
      await page.goto('/');
      await expect(page.getByText('식빵 모둠 5종')).toBeVisible();
      await page.getByRole('button', { name: '내 주변 · 3km' }).click();
      const dialog = page.getByRole('dialog');
      await expect(dialog).toBeVisible();
      const before = urls.length;
      await dialog.getByRole('button', { name: '5km', exact: true }).click();
      await expect(dialog.getByRole('button', { name: '5km', exact: true })).toHaveAttribute(
        'aria-pressed',
        'true',
      );
      expect(urls.length).toBe(before);
      await dialog.getByRole('button', { name: '적용' }).click();
      await expect.poll(() => urls.at(-1)?.searchParams.get('radius_km')).toBe('5');
      await expect(page.getByRole('button', { name: '내 주변 · 5km' })).toBeVisible();
      await expect(page.getByRole('dialog')).toHaveCount(0);
    });

    test('C1a: 10km 선택 뒤 Esc로 닫으면 요청이 없고, 다시 열면 3km가 선택돼 있다', async ({
      page,
    }) => {
      const urls = await mockOffers(page);
      await page.goto('/');
      await expect(page.getByText('식빵 모둠 5종')).toBeVisible();
      await page.getByRole('button', { name: '내 주변 · 3km' }).click();
      const before = urls.length;
      await page.getByRole('dialog').getByRole('button', { name: '10km', exact: true }).click();
      await page.keyboard.press('Escape');
      await expect(page.getByRole('dialog')).toHaveCount(0);
      expect(urls.length).toBe(before);
      await page.getByRole('button', { name: '내 주변 · 3km' }).click();
      await expect(
        page.getByRole('dialog').getByRole('button', { name: '3km', exact: true }),
      ).toHaveAttribute('aria-pressed', 'true');
      expect(urls.at(-1)?.searchParams.get('radius_km')).toBe('3');
    });
  });

  test.describe('위치 거부', () => {
    test.use({ permissions: [] });

    test('C1a: 위치 없음 → 5km 적용해도 lat·radius_km 없이 요청하고, 현재 위치 사용 뒤에도 lat이 없다', async ({
      page,
    }) => {
      const urls = await mockOffers(page, null);
      await page.goto('/');
      await expect(page.getByText('식빵 모둠 5종')).toBeVisible();
      await page.getByRole('button', { name: '위치 없음' }).click();
      const dialog = page.getByRole('dialog');
      await expect(dialog.getByText('지금: 위치 없음')).toBeVisible();
      await dialog.getByRole('button', { name: '5km', exact: true }).click();
      await dialog.getByRole('button', { name: '적용' }).click();
      await expect(page.getByRole('dialog')).toHaveCount(0);
      await page.getByRole('button', { name: '위치 없음' }).click();
      await page.getByRole('dialog').getByRole('button', { name: '◎ 현재 위치 사용' }).click();
      await expect(page.getByRole('dialog')).toBeVisible();
      expect(urls.length).toBeGreaterThan(0);
      for (const url of urls) {
        expect(url.searchParams.has('lat')).toBe(false);
        expect(url.searchParams.has('radius_km')).toBe(false);
      }
    });
  });
});

test('C1 → A1 → C1: 비로그인 「내 예약」 탭은 /login으로 가고, 로그인하면 홈으로 돌아온다', async ({
  page,
}) => {
  await mockOffers(page, null);
  await page.route('**/v1/auth/login', (route) =>
    json(route, { access_token: 'tok1', token_type: 'bearer', status: 'APPROVED' }),
  );
  await page.route('**/v1/users/me', (route) => json(route, userDto('CUSTOMER')));
  await page.goto('/');
  await expect(page.getByText('식빵 모둠 5종')).toBeVisible();
  await page.getByRole('link', { name: '내 예약' }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel('이메일').fill('owner@test.com');
  await page.getByLabel('비밀번호').fill('pw1234');
  await page.getByRole('button', { name: '로그인' }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByText('마감직전', { exact: true })).toBeVisible();
});

test('C1: 뷰포트 1280px에서도 앱 폭이 420px이다', async ({ page }) => {
  await mockOffers(page, null);
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto('/');
  await expect(page.getByText('식빵 모둠 5종')).toBeVisible();
  const box = await page.locator('.app').boundingBox();
  expect(box?.width).toBeCloseTo(420, -1);
});
