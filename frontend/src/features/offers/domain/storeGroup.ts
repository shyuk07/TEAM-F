import type { NearbyOffer } from './offer';

// 가게별 보기의 묶음(와이어프레임 밖 기능, 사용자 승인).
export type StoreGroup = {
  storeId: string;
  storeName: string;
  distanceKm: number | null;
  earliestSalesEnd: Date;
  offers: NearbyOffer[];
};

// 처음 나온 순서대로 가게를 묶는다(현재 정렬 유지). 가게 안 할인도 원래 순서.
// distanceKm는 null이 아닌 값 중 최소(모두 null이면 null), earliestSalesEnd는 최소 salesEnd.
export function groupByStore(items: NearbyOffer[]): StoreGroup[] {
  const groups = new Map<string, StoreGroup>();
  for (const item of items) {
    const { storeId, storeName, salesEnd } = item.offer;
    const group = groups.get(storeId);
    if (group === undefined) {
      groups.set(storeId, {
        storeId,
        storeName,
        distanceKm: item.distanceKm,
        earliestSalesEnd: salesEnd,
        offers: [item],
      });
      continue;
    }
    group.offers.push(item);
    group.distanceKm = minDistance(group.distanceKm, item.distanceKm);
    if (salesEnd < group.earliestSalesEnd) group.earliestSalesEnd = salesEnd;
  }
  return [...groups.values()];
}

function minDistance(a: number | null, b: number | null): number | null {
  if (a === null) return b;
  if (b === null) return a;
  return Math.min(a, b);
}
