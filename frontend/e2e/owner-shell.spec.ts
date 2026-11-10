// 백엔드 응답은 page.route로 대체
import { expect, test, type Page } from '@playwright/test';
import { mockOwnerSession } from './support/auth';

test.beforeEach(async ({ page }) => {
  await mockOwnerSession(page);
});

const TABS = ['오늘', '할인', '매장'] as const;

function tabBar(page: Page) {
  return page.locator('.tabs');
}

function topNav(page: Page) {
  return page.locator('.nav');
}

// 현재 뷰포트에서 보이는 내비게이션(mobile: TabBar, desktop: TopNav)
function visibleNav(page: Page, isMobile: boolean) {
  return isMobile ? tabBar(page) : topNav(page);
}

const TAB_SCREENS = [
  { id: 'O1', path: '/owner/today', title: 'O1 오늘', active: '오늘' },
  { id: 'O2', path: '/owner/offers', title: 'O2 할인', active: '할인' },
  { id: 'O4', path: '/owner/store', title: 'O4 매장', active: '매장' },
] as const;

for (const s of TAB_SCREENS) {
  test(`${s.id}: 뷰포트에 맞는 내비게이션만 보이고 현재 항목이 표시된다`, async ({
    page,
  }, testInfo) => {
    const isMobile = testInfo.project.name === 'mobile';
    await page.goto(s.path);
    await expect(page.getByRole('heading', { name: s.title })).toBeVisible();

    const shown = visibleNav(page, isMobile);
    const hidden = isMobile ? topNav(page) : tabBar(page);
    for (const label of TABS) {
      await expect(shown.getByRole('link', { name: label })).toBeVisible();
      await expect(hidden.getByRole('link', { name: label })).toBeHidden();
    }
    await expect(shown.locator('a[aria-current="page"]')).toHaveText(s.active);
  });
}

const SUB_SCREENS = [
  { id: 'O3', path: '/owner/offers/new', title: 'O3 할인 등록', active: '할인' },
  { id: 'O6', path: '/owner/products/new', title: 'O6 상품 등록', active: '매장' },
  { id: 'O11', path: '/owner/products/p1', title: 'O11 상품 수정', active: '매장' },
] as const;

for (const s of SUB_SCREENS) {
  test(`${s.id}: 하위 화면은 TabBar가 없고 데스크톱 TopNav 활성 항목이 소속 탭이다`, async ({
    page,
  }, testInfo) => {
    await page.goto(s.path);
    await expect(page.getByRole('heading', { name: s.title })).toBeVisible();
    await expect(tabBar(page)).toHaveCount(0);
    if (testInfo.project.name === 'desktop') {
      await expect(topNav(page).locator('a[aria-current="page"]')).toHaveText(s.active);
    }
  });
}

test('O1 → O4: 「매장」을 누르면 /owner/store로 이동하고 활성 항목이 바뀐다', async ({
  page,
}, testInfo) => {
  const isMobile = testInfo.project.name === 'mobile';
  await page.goto('/owner/today');
  const nav = visibleNav(page, isMobile);
  await expect(nav.locator('a[aria-current="page"]')).toHaveText('오늘');
  await nav.getByRole('link', { name: '매장' }).click();
  await expect(page).toHaveURL(/\/owner\/store$/);
  await expect(page.getByRole('heading', { name: 'O4 매장' })).toBeVisible();
  await expect(visibleNav(page, isMobile).locator('a[aria-current="page"]')).toHaveText('매장');
});

test('리다이렉트: /owner → /owner/today', async ({ page }) => {
  await page.goto('/owner');
  await expect(page).toHaveURL(/\/owner\/today$/);
  await expect(page.getByRole('heading', { name: 'O1 오늘' })).toBeVisible();
});

test('리다이렉트: /nope → /', async ({ page }) => {
  await page.goto('/nope');
  await expect(page).toHaveURL(/\/$/);
});

test('O11: /owner/products/p1 새로고침 후 같은 화면이다 (SPA fallback)', async ({ page }) => {
  await page.goto('/owner/products/p1');
  await expect(page.getByRole('heading', { name: 'O11 상품 수정' })).toBeVisible();
  await page.reload();
  await expect(page).toHaveURL(/\/owner\/products\/p1$/);
  await expect(page.getByRole('heading', { name: 'O11 상품 수정' })).toBeVisible();
  await expect(page.getByText('p1', { exact: true })).toBeVisible();
});
