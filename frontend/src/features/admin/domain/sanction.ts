export type SanctionKind =
  'rejectOwner' | 'suspendUser' | 'withdrawUser' | 'suspendStore' | 'closeStore' | 'suspendOffer';

export type SanctionCopy = { title: string; reasonLabel: string; submitLabel: string };

// TODO: 회원 정지 외 제재 시트의 제목·사유 라벨·버튼 문구는 같은 틀로 지은 임시 문구다.
//   왜: screens.md M2에 회원 정지 문구만 있다 (docs/design/frontend/admin.md D-5)
//   언제: 결정 후 (디자인 시스템: content.md 제재 시트 문구 확정)
const COPY: Record<SanctionKind, SanctionCopy> = {
  suspendUser: { title: '회원 정지', reasonLabel: '정지 사유 *', submitLabel: '정지하기' },
  rejectOwner: { title: '상점주 거부', reasonLabel: '거부 사유 *', submitLabel: '거부하기' },
  withdrawUser: { title: '강제 탈퇴', reasonLabel: '탈퇴 사유 *', submitLabel: '탈퇴시키기' },
  suspendStore: { title: '상점 정지', reasonLabel: '정지 사유 *', submitLabel: '정지하기' },
  closeStore: { title: '강제 폐점', reasonLabel: '폐점 사유 *', submitLabel: '폐점하기' },
  suspendOffer: { title: '할인 정지', reasonLabel: '정지 사유 *', submitLabel: '정지하기' },
};

export function sanctionCopy(kind: SanctionKind): SanctionCopy {
  return COPY[kind];
}

/** 정지 종료 입력은 회원 정지에만 있다 (screens.md M2). */
export function hasSuspensionEnd(kind: SanctionKind): boolean {
  return kind === 'suspendUser';
}

export const SUSPENSION_END_LABEL = '정지 종료 (비우면 무기한)';

/** 날짜 입력(YYYY-MM-DD)을 그날 23:59:59.999(현지 시각)로 바꾼다 (admin.md D-4). 형식이 틀리면 null. */
export function suspensionEnd(date: string): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(date);
  if (!m) return null;
  const y = Number(m[1]);
  const mo = Number(m[2]) - 1;
  const d = Number(m[3]);
  const end = new Date(y, mo, d, 23, 59, 59, 999);
  if (end.getFullYear() !== y || end.getMonth() !== mo || end.getDate() !== d) return null;
  return end;
}

export type SanctionInput = { reason: string; endDate: string };
export type ValidSanction = { reason: string; until: Date | null };
export type SanctionError = 'REASON_REQUIRED' | 'INVALID_END' | 'END_IN_PAST';

export type SanctionValidation =
  { ok: true; value: ValidSanction } | { ok: false; error: SanctionError };

export function validateSanction(
  kind: SanctionKind,
  input: SanctionInput,
  now: Date,
): SanctionValidation {
  const reason = input.reason.trim();
  if (reason === '') return { ok: false, error: 'REASON_REQUIRED' };
  if (!hasSuspensionEnd(kind) || input.endDate === '') {
    return { ok: true, value: { reason, until: null } };
  }
  const until = suspensionEnd(input.endDate);
  if (until === null) return { ok: false, error: 'INVALID_END' };
  if (until.getTime() <= now.getTime()) return { ok: false, error: 'END_IN_PAST' };
  return { ok: true, value: { reason, until } };
}

// 서버 오류 표(reference/admin.md §3)와 같은 뜻의 문구
const SANCTION_ERRORS: Record<SanctionError, string> = {
  REASON_REQUIRED: '사유를 입력해 주세요.',
  INVALID_END: '날짜를 다시 확인해 주세요.',
  END_IN_PAST: '정지 종료 시각은 현재 이후여야 합니다.',
};

export function sanctionErrorMessage(e: SanctionError): string {
  return SANCTION_ERRORS[e];
}
