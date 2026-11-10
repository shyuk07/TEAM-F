import { activeCustomerTab } from '@/widgets/customer-nav';

describe('activeCustomerTab', () => {
  it("'/' → home", () => {
    expect(activeCustomerTab('/')).toBe('home');
  });

  it("'/me/points' → me, '/reservations/' → reservations, '/ME' → me", () => {
    expect(activeCustomerTab('/me/points')).toBe('me');
    expect(activeCustomerTab('/reservations/')).toBe('reservations');
    expect(activeCustomerTab('/ME')).toBe('me');
  });

  it("'/offers/1'·'/login'·'/menu' → null", () => {
    expect(activeCustomerTab('/offers/1')).toBeNull();
    expect(activeCustomerTab('/login')).toBeNull();
    expect(activeCustomerTab('/menu')).toBeNull();
  });
});
