import { CUSTOMER_TABS, activeCustomerTab } from '@/widgets/customer-nav';
import { tabTarget } from '@/widgets/customer-nav/domain/customerTabs';

const [home, reservations, my] = CUSTOMER_TABS;

describe('CUSTOMER_TABS', () => {
  it('순서·라벨·경로', () => {
    expect(CUSTOMER_TABS.map((t) => [t.label, t.path])).toEqual([
      ['홈', '/'],
      ['내 예약', '/reservations'],
      ['마이', '/my'],
    ]);
  });
});

describe('activeCustomerTab', () => {
  it.each([
    ['/', 'home'],
    ['/reservations', 'reservations'],
    ['/reservations/', 'reservations'],
    ['/my', 'my'],
    ['/offers/abc', null],
    ['/MY', 'my'],
  ])('%s → %s', (pathname, expected) => {
    expect(activeCustomerTab(pathname)).toBe(expected);
  });
});

describe('tabTarget', () => {
  it('홈·anonymous → /', () => {
    expect(tabTarget(home, 'anonymous')).toEqual({ to: '/' });
  });

  it('내 예약·anonymous → /login, from /reservations', () => {
    expect(tabTarget(reservations, 'anonymous')).toEqual({
      to: '/login',
      state: { from: '/reservations' },
    });
  });

  it('마이·anonymous → /login, from /my', () => {
    expect(tabTarget(my, 'anonymous')).toEqual({ to: '/login', state: { from: '/my' } });
  });

  it('내 예약·authenticated → /reservations', () => {
    expect(tabTarget(reservations, 'authenticated')).toEqual({ to: '/reservations' });
  });

  it('내 예약·loading → /reservations(로딩 중에는 이동만)', () => {
    expect(tabTarget(reservations, 'loading')).toEqual({ to: '/reservations' });
  });

  it('마이·error → /my', () => {
    expect(tabTarget(my, 'error')).toEqual({ to: '/my' });
  });
});
