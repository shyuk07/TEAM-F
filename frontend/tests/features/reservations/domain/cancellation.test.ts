import {
  cancelAvailability,
  findPendingForOffer,
} from '@/features/reservations/domain/cancellation';
import { at, makeReservation } from '../fakes/reservations';

describe('cancelAvailability', () => {
  it('PENDING_PAYMENT는 취소 마감 뒤에도 cancellable, until null', () => {
    expect(cancelAvailability(makeReservation({ status: 'PENDING_PAYMENT' }), at(19))).toEqual({
      kind: 'cancellable',
      until: null,
    });
  });

  it('RESERVED, 16:59 → cancellable(until 17:00)', () => {
    expect(cancelAvailability(makeReservation(), at(16, 59))).toEqual({
      kind: 'cancellable',
      until: at(17),
    });
  });

  it('RESERVED, 취소 마감 정각 17:00 → cancellable', () => {
    expect(cancelAvailability(makeReservation(), at(17))).toEqual({
      kind: 'cancellable',
      until: at(17),
    });
  });

  it('RESERVED, 17:00:01 → deadlinePassed(until 17:00)', () => {
    expect(cancelAvailability(makeReservation(), at(17, 0, 1))).toEqual({
      kind: 'deadlinePassed',
      until: at(17),
    });
  });

  it.each([
    ['PICKED_UP', null],
    ['CANCELLED', 'CUSTOMER'],
    ['CANCELLED', 'STORE'],
  ] as const)('%s(%s) → none', (status, cancelledBy) => {
    expect(cancelAvailability(makeReservation({ status, cancelledBy }), at(16))).toEqual({
      kind: 'none',
    });
  });
});

describe('findPendingForOffer', () => {
  it('같은 offerId의 PENDING_PAYMENT 예약을 돌려준다', () => {
    const other = makeReservation({ id: 'x', offerId: 'o2', status: 'PENDING_PAYMENT' });
    const target = makeReservation({ id: 'y', offerId: 'o1', status: 'PENDING_PAYMENT' });
    expect(findPendingForOffer([other, target], 'o1')).toBe(target);
  });

  it('같은 offerId라도 RESERVED만 있으면 null', () => {
    expect(findPendingForOffer([makeReservation({ offerId: 'o1' })], 'o1')).toBeNull();
  });

  it('빈 배열이면 null', () => {
    expect(findPendingForOffer([], 'o1')).toBeNull();
  });
});
