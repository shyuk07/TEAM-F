import {
  displayState,
  isPickupMissed,
  statusLabel,
  statusTone,
} from '@/features/reservations/domain/display';
import { at, makeReservation } from '../fakes/reservations';

function view(over: Parameters<typeof makeReservation>[0], now: Date) {
  const s = displayState(makeReservation(over), now);
  return { state: s, label: statusLabel(s), tone: statusTone(s) };
}

describe('displayState·statusLabel·statusTone', () => {
  it('PENDING_PAYMENT → 결제 대기 / hot', () => {
    expect(view({ status: 'PENDING_PAYMENT' }, at(16))).toEqual({
      state: 'PENDING_PAYMENT',
      label: '결제 대기',
      tone: 'hot',
    });
  });

  it('RESERVED, 19:59 → 예약 확정 / ok', () => {
    expect(view({ status: 'RESERVED' }, at(19, 59))).toEqual({
      state: 'RESERVED',
      label: '예약 확정',
      tone: 'ok',
    });
  });

  it('RESERVED, 픽업 마감 정각 20:00 → 예약 확정(미수령 아님)', () => {
    expect(view({ status: 'RESERVED' }, at(20)).label).toBe('예약 확정');
  });

  it('RESERVED, 20:00:01 → 픽업 시간 지남 / mute', () => {
    expect(view({ status: 'RESERVED' }, at(20, 0, 1))).toEqual({
      state: 'PICKUP_MISSED',
      label: '픽업 시간 지남',
      tone: 'mute',
    });
  });

  it('PICKED_UP → 픽업 완료 / mute', () => {
    expect(view({ status: 'PICKED_UP' }, at(19))).toEqual({
      state: 'PICKED_UP',
      label: '픽업 완료',
      tone: 'mute',
    });
  });

  it('CANCELLED + CUSTOMER → 취소됨 / mute', () => {
    expect(view({ status: 'CANCELLED', cancelledBy: 'CUSTOMER' }, at(16))).toEqual({
      state: 'CANCELLED_BY_CUSTOMER',
      label: '취소됨',
      tone: 'mute',
    });
  });

  it('CANCELLED + STORE → 매장 사정으로 취소됨 / mute', () => {
    expect(view({ status: 'CANCELLED', cancelledBy: 'STORE' }, at(16))).toEqual({
      state: 'CANCELLED_BY_STORE',
      label: '매장 사정으로 취소됨',
      tone: 'mute',
    });
  });

  it('CANCELLED + null → 취소됨 / mute', () => {
    expect(view({ status: 'CANCELLED', cancelledBy: null }, at(16))).toEqual({
      state: 'CANCELLED',
      label: '취소됨',
      tone: 'mute',
    });
  });
});

describe('isPickupMissed', () => {
  it.each([
    ['RESERVED', at(20), false],
    ['RESERVED', at(20, 0, 1), true],
    ['PENDING_PAYMENT', at(21), false],
    ['PICKED_UP', at(21), false],
  ] as const)('%s, now %s → %s', (status, now, expected) => {
    expect(isPickupMissed(makeReservation({ status }), now)).toBe(expected);
  });
});
