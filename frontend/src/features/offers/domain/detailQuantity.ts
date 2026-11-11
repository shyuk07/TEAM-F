// 로그인 복귀 시 수량을 C2 주소의 ?qty=로 넘긴다(customer-home.md §5.6, offers.md D-5).
export const QUANTITY_PARAM = 'qty';

export function readQuantityParam(search: string): number | null {
  const raw = new URLSearchParams(search).get(QUANTITY_PARAM);
  // 상한은 자르지 않는다. 패널 clampQuantity가 min(남은 재고, 5)로 자른다(reservations.md D-1).
  return raw !== null && /^[1-9][0-9]*$/.test(raw) ? Number(raw) : null;
}

export function detailReturnPath(pathname: string, quantity: number): string {
  return `${pathname}?${QUANTITY_PARAM}=${quantity}`;
}
