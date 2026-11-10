// 현재 시각을 intervalMs(기본 30초)마다 갱신한다(customer-home.md D-14).
export function useNow(intervalMs?: number): Date {
  void intervalMs;
  throw new Error('not implemented: useNow');
}
