import { formatPoint } from './labels';

/** 「1,000」처럼 쉼표가 있어도 읽는다. 1 이상의 정수가 아니면 null. */
export function parseAmount(text: string): number | null {
  const t = text.replace(/,/g, '').trim();
  if (!/^\d+$/.test(t)) return null;
  const n = Number(t);
  if (!Number.isSafeInteger(n) || n < 1) return null;
  return n;
}

export type GrantError = 'AMOUNT_INVALID' | 'REASON_REQUIRED';
export type GrantValidation =
  { ok: true; value: { amount: number; reason: string } } | { ok: false; error: GrantError };

export function validateGrant(amountText: string, reason: string): GrantValidation {
  const amount = parseAmount(amountText);
  if (amount === null) return { ok: false, error: 'AMOUNT_INVALID' };
  const r = reason.trim();
  if (r === '') return { ok: false, error: 'REASON_REQUIRED' };
  return { ok: true, value: { amount, reason: r } };
}

// reference/admin.md §9 오류 문구
const GRANT_ERRORS: Record<GrantError, string> = {
  AMOUNT_INVALID: '지급 포인트는 1 이상이어야 합니다.',
  REASON_REQUIRED: '지급 사유를 입력해 주세요.',
};

export function grantErrorMessage(e: GrantError): string {
  return GRANT_ERRORS[e];
}

/** 버튼 문구에 금액을 넣는다 (screens.md M4 「1,000P 지급」). 금액이 없으면 「지급」. */
export function grantButtonLabel(amount: number | null): string {
  return amount === null ? '지급' : `${formatPoint(amount)} 지급`;
}

export function balanceAfterGrant(balance: number, amount: number | null): number {
  return amount === null ? balance : balance + amount;
}
