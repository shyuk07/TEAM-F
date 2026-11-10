function withCommas(n: number): string {
  return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

export function formatWon(n: number): string {
  return `${withCommas(n)}원`;
}

export function formatPlainPrice(n: number): string {
  return withCommas(n);
}

export function formatDiscountRate(rate: number): string {
  return `${rate}%`;
}

export function formatDistance(km: number | null): string | null {
  if (km === null) return null;
  // toFixed만으로는 0.35가 0.3이 되므로 먼저 반올림한다 (offers.md §3.2)
  return `${(Math.round(km * 10) / 10).toFixed(1)}km`;
}

export function formatStoreLine(storeName: string, km: number | null): string {
  const distance = formatDistance(km);
  return distance === null ? storeName : `${storeName} · ${distance}`;
}

export function formatRemaining(n: number): string {
  return `남은 ${n}개`;
}
