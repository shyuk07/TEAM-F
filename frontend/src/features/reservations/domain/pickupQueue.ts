import { isSameLocalDate } from '@/shared/lib/format';
import type { StoreReservation } from './storeReservation';

export function isSameLocalDay(d1: Date, d2: Date): boolean {
  return isSameLocalDate(d1, d2);
}

// TODO: 「완료」 범위를 예약 시각 기준으로 임시 정했다
//   왜: 완료 시각이 목록에 없다 (owner-today.md D-4, Q-3)
//   언제: 결정 후 (사용자: 오늘의 정의)
export function splitQueue(
  items: StoreReservation[],
  now: Date,
): {
  waiting: StoreReservation[];
  doneToday: StoreReservation[];
} {
  const waiting: StoreReservation[] = [];
  const doneToday: StoreReservation[] = [];

  for (const item of items) {
    if (item.status === 'RESERVED') {
      waiting.push(item);
    } else if (item.status === 'PICKED_UP' && isSameLocalDay(item.createdAt, now)) {
      doneToday.push(item);
    }
  }

  return { waiting, doneToday };
}

export function queueCounts(
  waiting: StoreReservation[],
  doneToday: StoreReservation[],
): {
  waiting: number;
  done: number;
} {
  return {
    waiting: waiting.length,
    done: doneToday.length,
  };
}
