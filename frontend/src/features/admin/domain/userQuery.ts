import type { AdminAccountStatus, AdminRole } from './adminUser';

export type UserListQuery = {
  role?: AdminRole;
  status?: AdminAccountStatus;
  email?: string;
  page: number;
  size: number;
};

export const PAGE_SIZE = 20;

export type MemberFilter = 'all' | 'customer' | 'owner' | 'suspended' | 'withdrawn';

// screens.md M3 칩: 전체 / 고객 / 상점주 / 정지 / 탈퇴
export const MEMBER_FILTERS: readonly { key: MemberFilter; label: string }[] = [
  { key: 'all', label: '전체' },
  { key: 'customer', label: '고객' },
  { key: 'owner', label: '상점주' },
  { key: 'suspended', label: '정지' },
  { key: 'withdrawn', label: '탈퇴' },
];

export function memberFilterQuery(f: MemberFilter): Pick<UserListQuery, 'role' | 'status'> {
  switch (f) {
    case 'all':
      return {};
    case 'customer':
      return { role: 'CUSTOMER' };
    case 'owner':
      return { role: 'OWNER' };
    case 'suspended':
      return { status: 'SUSPENDED' };
    case 'withdrawn':
      return { status: 'WITHDRAWN' };
  }
}

export const APPROVAL_FILTER: Pick<UserListQuery, 'role' | 'status'> = {
  role: 'OWNER',
  status: 'PENDING',
};

/** 빈 칸·공백은 검색어 없음으로 본다. */
export function normalizeEmailSearch(text: string): string | undefined {
  const t = text.trim();
  return t === '' ? undefined : t;
}

export function queryKey(q: UserListQuery): string {
  return [q.role ?? '', q.status ?? '', q.email ?? '', q.page, q.size].join('|');
}

export type PageSummary = { text: string; hasPrev: boolean; hasNext: boolean };

// 「1–20 / 134명」 (page는 1부터)
export function pageSummary(page: number, size: number, total: number): PageSummary {
  if (total <= 0) return { text: '0 / 0명', hasPrev: page > 1, hasNext: false };
  const from = (page - 1) * size + 1;
  const to = Math.min(page * size, total);
  return {
    text: `${from}–${to} / ${total.toLocaleString('ko-KR')}명`,
    hasPrev: page > 1,
    hasNext: page * size < total,
  };
}

// 회원 탭의 검색·필터·페이지는 주소(쿼리)에 둔다. 상세로 갔다 와도 목록 상태가 남는다.
export type MemberSearch = { filter: MemberFilter; email: string; page: number };

export const DEFAULT_MEMBER_SEARCH: MemberSearch = { filter: 'all', email: '', page: 1 };

function isMemberFilter(v: string | null): v is MemberFilter {
  return MEMBER_FILTERS.some((f) => f.key === v);
}

export function readMemberSearch(get: (key: string) => string | null): MemberSearch {
  const filter = get('filter');
  const page = Number(get('page'));
  return {
    filter: isMemberFilter(filter) ? filter : 'all',
    email: get('email') ?? '',
    page: Number.isInteger(page) && page >= 1 ? page : 1,
  };
}

/** 기본값은 뺀 쿼리 문자열(앞에 ? 포함, 없으면 빈 문자열) */
export function memberSearchString(s: MemberSearch): string {
  const parts: string[] = [];
  if (s.filter !== 'all') parts.push(`filter=${encodeURIComponent(s.filter)}`);
  if (s.email.trim() !== '') parts.push(`email=${encodeURIComponent(s.email.trim())}`);
  if (s.page !== 1) parts.push(`page=${s.page}`);
  return parts.length === 0 ? '' : `?${parts.join('&')}`;
}

export function memberListQuery(s: MemberSearch): UserListQuery {
  return {
    ...memberFilterQuery(s.filter),
    email: normalizeEmailSearch(s.email),
    page: s.page,
    size: PAGE_SIZE,
  };
}
