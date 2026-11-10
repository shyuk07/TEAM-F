import {
  accountStatusView,
  displayName,
  formatPoint,
  formatShortDate,
  formatSignedPoint,
  maskPhone,
  offerStatusView,
  pointTypeLabel,
  storeStatusView,
} from '@/features/admin/domain/labels';
import {
  balanceAfterGrant,
  grantButtonLabel,
  parseAmount,
  validateGrant,
} from '@/features/admin/domain/pointGrant';
import {
  hasSuspensionEnd,
  sanctionCopy,
  suspensionEnd,
  validateSanction,
} from '@/features/admin/domain/sanction';
import { availableUserActions, canReview } from '@/features/admin/domain/userActions';
import {
  memberFilterQuery,
  memberListQuery,
  memberSearchString,
  pageSummary,
  readMemberSearch,
} from '@/features/admin/domain/userQuery';
import { isUuid } from '@/features/admin/domain/uuid';

describe('labels', () => {
  it.each([
    ['PENDING', '승인 대기', 'hot'],
    ['APPROVED', '정상', null],
    ['REJECTED', '거절됨', 'mute'],
    ['SUSPENDED', '정지', 'hot'],
    ['WITHDRAWN', '탈퇴', 'mute'],
  ] as const)('회원 %s → %s', (status, text, tone) => {
    expect(accountStatusView(status)).toEqual({ text, tone });
  });

  it('상점·할인 상태 문구, 모르는 코드는 코드 그대로', () => {
    expect(storeStatusView('ACTIVE')).toEqual({ text: '영업 중', tone: 'ok' });
    expect(storeStatusView('CLOSED')).toEqual({ text: '폐점', tone: 'mute' });
    expect(offerStatusView('SUSPENDED')).toEqual({ text: '할인 정지', tone: 'hot' });
    expect(offerStatusView('SOLD_OUT')).toEqual({ text: 'SOLD_OUT', tone: null });
  });

  it('포인트 종류는 한국어, 모르는 코드는 그대로', () => {
    expect(pointTypeLabel('EARN')).toBe('적립');
    expect(pointTypeLabel('GRANT')).toBe('지급');
    expect(pointTypeLabel('EXPIRE')).toBe('소멸');
    expect(pointTypeLabel('NEW')).toBe('NEW');
  });

  it('포인트 표기: 쉼표, 부호(마이너스는 U+2212)', () => {
    expect(formatPoint(2300)).toBe('2,300P');
    expect(formatSignedPoint(115)).toBe('+115P');
    expect(formatSignedPoint(-500)).toBe('−500P');
    expect(formatSignedPoint(0)).toBe('+0P');
  });

  it('날짜는 MM/DD', () => {
    expect(formatShortDate(new Date(2026, 10, 8))).toBe('11/08');
  });

  it('이름이 없거나 공백이면 이메일', () => {
    expect(displayName({ name: '박고객', email: 'a@b.c' })).toBe('박고객');
    expect(displayName({ name: null, email: 'a@b.c' })).toBe('a@b.c');
    expect(displayName({ name: '  ', email: 'a@b.c' })).toBe('a@b.c');
  });

  it('전화번호 가운데를 가린다', () => {
    expect(maskPhone('010-1234-5678')).toBe('010-****-5678');
    expect(maskPhone('01012345678')).toBe('*******5678');
    expect(maskPhone(null)).toBe('');
    expect(maskPhone('123')).toBe('123');
  });
});

describe('userQuery', () => {
  it('칩 → 쿼리', () => {
    expect(memberFilterQuery('all')).toEqual({});
    expect(memberFilterQuery('owner')).toEqual({ role: 'OWNER' });
    expect(memberFilterQuery('suspended')).toEqual({ status: 'SUSPENDED' });
  });

  it('페이지 요약', () => {
    expect(pageSummary(1, 20, 134)).toEqual({
      text: '1–20 / 134명',
      hasPrev: false,
      hasNext: true,
    });
    expect(pageSummary(7, 20, 134)).toEqual({
      text: '121–134 / 134명',
      hasPrev: true,
      hasNext: false,
    });
    expect(pageSummary(1, 20, 20).hasNext).toBe(false);
    expect(pageSummary(1, 20, 0)).toEqual({ text: '0 / 0명', hasPrev: false, hasNext: false });
  });

  it('주소 쿼리 읽기: 잘못된 값은 기본값', () => {
    const q = new URLSearchParams('filter=owner&email=a%40b&page=3');
    expect(readMemberSearch((k) => q.get(k))).toEqual({ filter: 'owner', email: 'a@b', page: 3 });
    const bad = new URLSearchParams('filter=hacker&page=-1');
    expect(readMemberSearch((k) => bad.get(k))).toEqual({ filter: 'all', email: '', page: 1 });
    const frac = new URLSearchParams('page=1.5');
    expect(readMemberSearch((k) => frac.get(k)).page).toBe(1);
  });

  it('주소 쿼리 만들기: 기본값은 뺀다', () => {
    expect(memberSearchString({ filter: 'all', email: '', page: 1 })).toBe('');
    expect(memberSearchString({ filter: 'withdrawn', email: ' a@b ', page: 2 })).toBe(
      '?filter=withdrawn&email=a%40b&page=2',
    );
  });

  it('목록 쿼리: 공백 검색어는 없음', () => {
    expect(memberListQuery({ filter: 'customer', email: '  ', page: 2 })).toEqual({
      role: 'CUSTOMER',
      email: undefined,
      page: 2,
      size: 20,
    });
  });
});

describe('sanction', () => {
  const now = new Date(2026, 10, 10, 12, 0);

  it('회원 정지 문구는 screens.md M2 그대로', () => {
    expect(sanctionCopy('suspendUser')).toEqual({
      title: '회원 정지',
      reasonLabel: '정지 사유 *',
      submitLabel: '정지하기',
    });
  });

  it('정지 종료는 회원 정지에만', () => {
    expect(hasSuspensionEnd('suspendUser')).toBe(true);
    expect(hasSuspensionEnd('suspendStore')).toBe(false);
  });

  it('사유가 비거나 공백이면 거부', () => {
    expect(validateSanction('rejectOwner', { reason: '  ', endDate: '' }, now)).toEqual({
      ok: false,
      error: 'REASON_REQUIRED',
    });
  });

  it('종료일 없으면 무기한, 사유는 앞뒤 공백 제거', () => {
    expect(validateSanction('suspendUser', { reason: ' 노쇼 반복 ', endDate: '' }, now)).toEqual({
      ok: true,
      value: { reason: '노쇼 반복', until: null },
    });
  });

  it('종료일은 그날 끝(23:59:59.999)', () => {
    expect(suspensionEnd('2026-11-30')).toEqual(new Date(2026, 10, 30, 23, 59, 59, 999));
    expect(suspensionEnd('2026-02-30')).toBeNull();
    expect(suspensionEnd('11/30')).toBeNull();
  });

  it('오늘 날짜는 아직 끝나지 않았으므로 허용, 어제는 거부', () => {
    const today = validateSanction('suspendUser', { reason: 'x', endDate: '2026-11-10' }, now);
    expect(today.ok).toBe(true);
    expect(validateSanction('suspendUser', { reason: 'x', endDate: '2026-11-09' }, now)).toEqual({
      ok: false,
      error: 'END_IN_PAST',
    });
  });

  it('정지가 아닌 제재는 종료일을 무시', () => {
    const v = validateSanction('suspendStore', { reason: 'x', endDate: '2020-01-01' }, now);
    expect(v).toEqual({ ok: true, value: { reason: 'x', until: null } });
  });
});

describe('pointGrant', () => {
  it.each([
    ['1,000', 1000],
    [' 5 ', 5],
    ['0', null],
    ['-5', null],
    ['1.5', null],
    ['', null],
    ['abc', null],
  ])('parseAmount(%j) = %j', (text, expected) => {
    expect(parseAmount(text)).toBe(expected);
  });

  it('검증: 금액 먼저, 그다음 사유', () => {
    expect(validateGrant('0', '')).toEqual({ ok: false, error: 'AMOUNT_INVALID' });
    expect(validateGrant('100', ' ')).toEqual({ ok: false, error: 'REASON_REQUIRED' });
    expect(validateGrant('100', ' 보상 ')).toEqual({
      ok: true,
      value: { amount: 100, reason: '보상' },
    });
  });

  it('버튼 문구에 금액, 지급 후 잔액', () => {
    expect(grantButtonLabel(1000)).toBe('1,000P 지급');
    expect(grantButtonLabel(null)).toBe('지급');
    expect(balanceAfterGrant(2300, 1000)).toBe(3300);
    expect(balanceAfterGrant(2300, null)).toBe(2300);
  });
});

describe('userActions', () => {
  it('정상 고객은 모두 가능', () => {
    expect(availableUserActions({ role: 'CUSTOMER', status: 'APPROVED' })).toEqual({
      grantPoints: true,
      suspend: true,
      withdraw: true,
    });
  });

  it('탈퇴 회원은 아무것도 못 함', () => {
    expect(availableUserActions({ role: 'CUSTOMER', status: 'WITHDRAWN' })).toEqual({
      grantPoints: false,
      suspend: false,
      withdraw: false,
    });
  });

  it('관리자 계정은 정지·탈퇴 불가, 정지 회원은 다시 정지 불가, 승인 대기는 정지 불가', () => {
    expect(availableUserActions({ role: 'ADMIN', status: 'APPROVED' }).suspend).toBe(false);
    expect(availableUserActions({ role: 'ADMIN', status: 'APPROVED' }).withdraw).toBe(false);
    expect(availableUserActions({ role: 'CUSTOMER', status: 'SUSPENDED' }).suspend).toBe(false);
    expect(availableUserActions({ role: 'OWNER', status: 'PENDING' }).suspend).toBe(false);
  });

  it('승인·거부는 승인 대기 상점주만', () => {
    expect(canReview({ role: 'OWNER', status: 'PENDING' })).toBe(true);
    expect(canReview({ role: 'OWNER', status: 'APPROVED' })).toBe(false);
    expect(canReview({ role: 'CUSTOMER', status: 'PENDING' })).toBe(false);
  });
});

describe('isUuid', () => {
  it('UUID만 통과', () => {
    expect(isUuid('1a2b3c4d-1111-4111-8111-111111111111')).toBe(true);
    expect(isUuid(' 1A2B3C4D-1111-4111-8111-111111111111 ')).toBe(true);
    expect(isUuid('1a2b3c4d')).toBe(false);
    expect(isUuid('')).toBe(false);
  });
});
