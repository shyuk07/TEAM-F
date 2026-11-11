import type { Reservation } from '@/features/reservations';

/** KST(+09:00) 기준 2026-11-10 h:m:s 순간을 만든다. 표시가 Asia/Seoul 고정이라 실행 환경 시간대와 무관하다. */
export function at(h: number, m = 0, s = 0): Date {
  const p = (n: number) => String(n).padStart(2, '0');
  return new Date(`2026-11-10T${p(h)}:${p(m)}:${p(s)}+09:00`);
}

/** 공통 픽스처: 픽업 18:00–20:00, 취소 마감 17:00, 예약 시각 15:30. */
export function makeReservation(over: Partial<Reservation> = {}): Reservation {
  return {
    id: 'r1',
    offerId: 'o1',
    storeName: '망원베이커리',
    productName: '식빵 모둠',
    quantity: 2,
    totalPrice: 11500,
    status: 'RESERVED',
    createdAt: at(15, 30),
    pickupCode: 'A12345',
    pickupAddress: '서울 마포구 망원로 1',
    cancelledBy: null,
    pickupStart: at(18),
    pickupEnd: at(20),
    cancellableUntil: at(17),
    ...over,
  };
}
