import type { Page, Route } from '@playwright/test';

export const TOKEN_KEY = 'lastcall.accessToken';

export function userDto(role: 'OWNER' | 'CUSTOMER' | 'ADMIN' = 'OWNER') {
  return {
    id: '00000000-0000-0000-0000-000000000001',
    email: 'owner@test.com',
    name: '김사장',
    phone: null,
    role,
    users_point: 0,
    created_at: '2026-01-01T00:00:00Z',
    status: 'APPROVED',
  };
}

export function errorBody(status: number, errorCode: string, message: string) {
  return {
    status,
    contentType: 'application/json',
    body: JSON.stringify({ success: false, error_code: errorCode, message }),
  };
}

export function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
}

// 토큰을 미리 심고 /v1/users/me가 OWNER를 돌려주게 한다.
export async function mockOwnerSession(page: Page) {
  await page.addInitScript((key) => {
    // 탭에서 한 번만 심는다(로그아웃 뒤 다시 이동해도 토큰이 되살아나지 않게)
    if (sessionStorage.getItem('e2e-seeded') === null) {
      sessionStorage.setItem('e2e-seeded', '1');
      localStorage.setItem(key, 't');
    }
  }, TOKEN_KEY);
  await page.route('**/v1/users/me', (route) => json(route, userDto('OWNER')));
}
