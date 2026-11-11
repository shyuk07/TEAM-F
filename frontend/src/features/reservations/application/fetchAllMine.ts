import type { ReservationRepository } from '../domain/ports';
import type { Reservation, ReservationStatus } from '../domain/reservation';

const PAGE_SIZE = 100;

// TODO: 지난 예약 「더 보기」가 없다. size=100으로 전 페이지를 받아 앱에서 탭을 나눈다.
//   왜: 진행 중/지난 분류가 pickup_end 기준 화면 계산이라 서버 status 필터로 탭을 나눌 수 없다 (docs/design/frontend/reservations.md D-7)
//   언제: 결정 후 (사용자: 지난 예약 페이지 방식)
export async function fetchAllMine(
  repo: ReservationRepository,
  signal: AbortSignal,
  status?: ReservationStatus,
): Promise<Reservation[]> {
  const all: Reservation[] = [];
  for (let page = 1; ; page++) {
    const query =
      status === undefined ? { page, size: PAGE_SIZE } : { status, page, size: PAGE_SIZE };
    const res = await repo.listMine(query, signal);
    all.push(...res.items);
    if (res.items.length === 0 || all.length >= res.total) return all;
  }
}
