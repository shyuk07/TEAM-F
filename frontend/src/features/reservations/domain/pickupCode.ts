export const PICKUP_CODE_MAX = 20;

export type PickupCodeIssue = 'empty' | 'too-long';

export function normalizePickupCode(raw: string): string {
  return raw.trim();
}

export function validatePickupCode(raw: string): PickupCodeIssue | null {
  const normalized = normalizePickupCode(raw);
  if (!normalized) {
    return 'empty';
  }
  if (normalized.length > PICKUP_CODE_MAX) {
    return 'too-long';
  }
  return null;
}
