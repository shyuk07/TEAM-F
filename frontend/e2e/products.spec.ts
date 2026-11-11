// 백엔드 응답은 page.route로 대체 (모킹). 상점·상품 API를 상태 있는 가짜로 둔다.
// 범위: O4 → O6 등록 → O4 목록 반영 → O11 이름 수정 → 숨기기·다시 보이기 → O4 태그 (사진 바꾸기·삭제는 B-1로 제외)
import { expect, test, type Page, type Route } from '@playwright/test';
import { json, mockOwnerSession } from './support/auth';

const STORE_ID = 'st-1';
const PRODUCT_ID = 'p-new';

const storeDto = {
  id: STORE_ID,
  owner_id: '00000000-0000-0000-0000-000000000001',
  name: '망원베이커리',
  pickup_address: '서울시 마포구 망원로 10',
  latitude: null,
  longitude: null,
  created_at: '2026-01-01T00:00:00Z',
  approval_at: '2026-01-02T00:00:00Z',
  closed_at: null,
  status: 'ACTIVE',
};

type ProductState = {
  id: string;
  store_id: string;
  name: string;
  category: string | null;
  description: string | null;
  original_price: number;
  is_active: boolean;
  product_image: string[];
};

// 현재 뷰포트에서 보이는 버튼(본문 .dk와 CtaBar .cta 두 벌)을 누른다.
function visibleButton(page: Page, name: string) {
  return page.getByRole('button', { name }).filter({ visible: true }).first();
}

async function mockProducts(page: Page) {
  let product: ProductState | null = null;
  const created: string[] = [];

  await page.route('**/v1/stores/me', (route) => json(route, storeDto));

  // GET 목록 / POST 등록(multipart)
  await page.route(/\/v1\/stores\/st-1\/products(\?.*)?$/, (route: Route) => {
    const req = route.request();
    if (req.method() === 'POST') {
      created.push(req.postData() ?? '');
      product = {
        id: PRODUCT_ID,
        store_id: STORE_ID,
        name: '식빵',
        category: null,
        description: null,
        original_price: 12000,
        is_active: true,
        product_image: [],
      };
      return json(route, product, 201);
    }
    const items = product === null ? [] : [product];
    return json(route, { items, page: 1, size: 100, total: items.length });
  });

  // GET 단건 / PATCH 수정
  await page.route(/\/v1\/products\/p-new$/, (route) => {
    const req = route.request();
    if (product === null) return json(route, { success: false, error_code: 'NOT_FOUND' }, 404);
    if (req.method() === 'PATCH') {
      const body = req.postDataJSON() as Partial<ProductState>;
      product = { ...product, ...body };
    }
    return json(route, product);
  });

  await page.route(/\/v1\/products\/p-new\/deactivate$/, (route) => {
    if (product === null) return json(route, { success: false, error_code: 'NOT_FOUND' }, 404);
    product = { ...product, is_active: false };
    return json(route, product);
  });
  await page.route(/\/v1\/products\/p-new\/activate$/, (route) => {
    if (product === null) return json(route, { success: false, error_code: 'NOT_FOUND' }, 404);
    product = { ...product, is_active: true };
    return json(route, product);
  });

  return { created };
}

// 등록 제출(「등록만」). 모바일은 하단 CtaBar(.cta), 데스크톱(720px 이상)은 오른쪽 열(.dk)의 버튼이 보인다(D-37).
// visibleButton이 현재 뷰포트에서 보이는 쪽을 누른다.
async function submitCreate(page: Page) {
  await visibleButton(page, '등록만').click();
  await expect(page).toHaveURL(/\/owner\/store$/);
}

// multipart 본문에서 한 파트의 값을 읽는다(파트 헤더 뒤 빈 줄 다음 한 줄).
function partValue(body: string, name: string) {
  return new RegExp(`name="${name}"\\r?\\n\\r?\\n([^\\r\\n]*)`).exec(body)?.[1];
}

test.beforeEach(async ({ page }) => {
  await mockOwnerSession(page);
});

test('O4 → O6 → O4 → O11: 상품 등록, 이름 수정, 숨기기·다시 보이기', async ({ page }) => {
  const { created } = await mockProducts(page);

  // O4: 빈 상태
  await page.goto('/owner/store');
  await expect(page.getByText('아직 등록한 상품이 없어요')).toBeVisible();
  await page.getByRole('link', { name: '상품 등록' }).click();
  await expect(page).toHaveURL(/\/owner\/products\/new$/);

  // O6: 입력 → 「등록만」
  await page.getByLabel(/^상품명/).fill('식빵');
  await page.getByLabel(/^정상 가격/).fill('12000');
  await submitCreate(page);

  // O4: 목록에 새 상품. 입력한 이름·가격이 그대로 전송되고, 카테고리·설명·파일이 없으면 multipart에 실리지 않는다
  await expect(page.getByText('상품 1개')).toBeVisible();
  await expect(page.getByRole('link', { name: /식빵/ })).toBeVisible();
  expect(created).toHaveLength(1);
  expect(partValue(created[0], 'name')).toBe('식빵');
  expect(partValue(created[0], 'original_price')).toBe('12000');
  expect(created[0]).not.toContain('name="file"');
  expect(created[0]).not.toContain('name="category"');
  expect(created[0]).not.toContain('name="description"');

  // O11: 이름 수정 → 저장 → O4에 반영
  await page.getByRole('link', { name: /식빵/ }).click();
  await expect(page).toHaveURL(/\/owner\/products\/p-new$/);
  await expect(page.getByLabel(/^상품명/)).toHaveValue('식빵');
  await page.getByLabel(/^상품명/).fill('우유 식빵');
  await visibleButton(page, '저장').click();
  await expect(page).toHaveURL(/\/owner\/store$/);
  await expect(page.getByRole('link', { name: /우유 식빵/ })).toBeVisible();

  // O11: 숨기기(확인 없음) → 칩 「숨김」, 「다시 보이기」 → 칩 「노출 중」
  await page.getByRole('link', { name: /우유 식빵/ }).click();
  await expect(page.getByText('노출 중')).toBeVisible();
  await page.getByText('숨기기', { exact: true }).click();
  await expect(page.getByText('숨김', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: '다시 보이기' }).click();
  await expect(page.getByText('노출 중')).toBeVisible();

  // 다시 숨긴 뒤 O4 목록의 태그 「숨김」
  await page.getByText('숨기기', { exact: true }).click();
  await expect(page.getByText('숨김', { exact: true })).toBeVisible();
  await page.getByRole('link', { name: '뒤로' }).click();
  await expect(page).toHaveURL(/\/owner\/store$/);
  await expect(page.getByText('숨김', { exact: true })).toBeVisible();
});

test('O6: 사진을 골라 등록하면 multipart에 이름·가격·file 파트가 실린다', async ({ page }) => {
  const { created } = await mockProducts(page);
  await page.goto('/owner/products/new');
  await page.getByLabel(/^상품명/).fill('호밀빵');
  await page.getByLabel(/^정상 가격/).fill('8500');
  await page.getByRole('button', { name: /사진 추가/ }).click();
  await page.locator('input[type="file"]:not([capture])').setInputFiles({
    name: 'bread.png',
    mimeType: 'image/png',
    buffer: Buffer.from('89504e470d0a1a0a', 'hex'),
  });
  await expect(page.getByRole('button', { name: '사진 바꾸기' })).toBeVisible();
  await submitCreate(page);
  expect(created).toHaveLength(1);
  expect(partValue(created[0], 'name')).toBe('호밀빵');
  expect(partValue(created[0], 'original_price')).toBe('8500');
  expect(created[0]).toContain('name="file"');
  expect(created[0]).toContain('bread.png');
});

test('O11: /owner/products/p-new 새로고침 후 같은 화면이다 (SPA fallback)', async ({ page }) => {
  await mockProducts(page);
  await page.goto('/owner/store');
  await page.getByRole('link', { name: '상품 등록' }).click();
  await page.getByLabel(/^상품명/).fill('식빵');
  await page.getByLabel(/^정상 가격/).fill('12000');
  await submitCreate(page);
  await page.goto('/owner/products/p-new');
  await page.reload();
  await expect(page).toHaveURL(/\/owner\/products\/p-new$/);
  await expect(page.getByLabel(/^상품명/)).toHaveValue('식빵');
});

test('O11: 존재하지 않는 상품은 「상품을 찾을 수 없어요.」와 「매장으로」', async ({ page }) => {
  await mockProducts(page);
  await page.goto('/owner/products/p-new');
  await expect(page.getByText('상품을 찾을 수 없어요.')).toBeVisible();
  await page.getByRole('link', { name: '매장으로' }).click();
  await expect(page).toHaveURL(/\/owner\/store$/);
});
