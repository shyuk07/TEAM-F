// 서버 최대 500자 (reference/stores.md §1, backend schemas.py:9)
export const PICKUP_ADDRESS_MAX_LENGTH = 500;

export function canSubmitOpenStore(address: string): boolean {
  const trimmed = address.trim();
  return trimmed.length >= 1 && trimmed.length <= PICKUP_ADDRESS_MAX_LENGTH;
}
