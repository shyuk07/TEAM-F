import { isVisibleToCustomer, splitByTab, tabOf } from '@/features/reservations/domain/grouping';
import { at, makeReservation } from '../fakes/reservations';

describe('tabOf', () => {
  it.each([
    ['PENDING_PAYMENT', null, at(21), 'active'],
    ['RESERVED', null, at(20), 'active'],
    ['RESERVED', null, at(20, 0, 1), 'past'],
    ['PICKED_UP', null, at(19), 'past'],
    ['CANCELLED', 'CUSTOMER', at(16), 'past'],
    ['CANCELLED', 'STORE', at(20), 'active'],
    ['CANCELLED', 'STORE', at(20, 0, 1), 'past'],
  ] as const)('%s + %s, now %s → %s', (status, cancelledBy, now, expected) => {
    expect(tabOf(makeReservation({ status, cancelledBy }), now)).toBe(expected);
  });
});

describe('isVisibleToCustomer', () => {
  it('SYSTEM 취소는 보이지 않는다', () => {
    expect(
      isVisibleToCustomer(makeReservation({ status: 'CANCELLED', cancelledBy: 'SYSTEM' })),
    ).toBe(false);
  });

  it('CUSTOMER 취소는 보인다', () => {
    expect(
      isVisibleToCustomer(makeReservation({ status: 'CANCELLED', cancelledBy: 'CUSTOMER' })),
    ).toBe(true);
  });
});

describe('splitByTab', () => {
  it('SYSTEM 취소는 두 탭 어디에도 없다', () => {
    const sys = makeReservation({ id: 'sys', status: 'CANCELLED', cancelledBy: 'SYSTEM' });
    const { active, past } = splitByTab([sys], at(16));
    expect(active).toEqual([]);
    expect(past).toEqual([]);
  });

  it('각 탭을 createdAt 내림차순으로 나눈다', () => {
    const a1 = makeReservation({ id: 'a1', status: 'RESERVED', createdAt: at(10) });
    const a2 = makeReservation({ id: 'a2', status: 'PENDING_PAYMENT', createdAt: at(12) });
    const p1 = makeReservation({ id: 'p1', status: 'PICKED_UP', createdAt: at(9) });
    const p2 = makeReservation({
      id: 'p2',
      status: 'CANCELLED',
      cancelledBy: 'CUSTOMER',
      createdAt: at(11),
    });
    const { active, past } = splitByTab([a1, p1, a2, p2], at(16));
    expect(active.map((r) => r.id)).toEqual(['a2', 'a1']);
    expect(past.map((r) => r.id)).toEqual(['p2', 'p1']);
  });

  it('빈 배열이면 두 탭 모두 빈 배열이다', () => {
    expect(splitByTab([], at(16))).toEqual({ active: [], past: [] });
  });
});
