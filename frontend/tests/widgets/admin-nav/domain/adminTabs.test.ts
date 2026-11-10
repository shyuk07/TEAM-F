import { ADMIN_TABS, activeAdminTab } from '@/widgets/admin-nav';

describe('adminTabs', () => {
  it('탭 4개: 승인 회원 상점 할인', () => {
    expect(ADMIN_TABS.map((t) => t.label)).toEqual(['승인', '회원', '상점', '할인']);
  });

  it.each([
    ['/admin/approvals', 'approvals'],
    ['/admin/users', 'users'],
    ['/admin/users/abc', 'users'],
    ['/ADMIN/Stores/', 'stores'],
    ['/admin/offers', 'offers'],
    ['/admin/usersx', null],
    ['/admin', null],
  ])('%s → %s', (path, key) => {
    expect(activeAdminTab(path)).toBe(key);
  });
});
