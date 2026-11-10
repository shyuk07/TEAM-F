import {
  WITHDRAW_PASSWORD_MISMATCH_MESSAGE,
  withdrawErrorView,
} from '@/features/auth/domain/accountMessages';
import {
  formatPoint,
  formatPointDelta,
  pointExpiryText,
  pointLogMeta,
  pointTypeLabel,
  type PointType,
} from '@/features/auth/domain/points';
import { makePointLog } from '../fakes/points';

describe('pointTypeLabel', () => {
  it('6종을 한국어로 바꾼다', () => {
    const table: Record<PointType, string> = {
      EARN: '적립',
      USE: '사용',
      RESTORE: '복구',
      REVOKE: '회수',
      GRANT: '지급',
      EXPIRE: '소멸',
    };
    for (const [type, label] of Object.entries(table)) {
      expect(pointTypeLabel(type as PointType)).toBe(label);
    }
  });
});

describe('formatPointDelta', () => {
  it.each<[number, string]>([
    [115, '+115P'],
    [-500, '−500P'],
    [1000, '+1,000P'],
    [0, '0P'],
  ])('%d → %s', (n, expected) => {
    expect(formatPointDelta(n)).toBe(expected);
  });
});

describe('formatPoint', () => {
  it('1240 → 1,240P', () => {
    expect(formatPoint(1240)).toBe('1,240P');
  });
});

describe('pointLogMeta', () => {
  it("short → 'MM/DD'", () => {
    expect(pointLogMeta(makePointLog(), 'short')).toBe('11/07');
  });

  it("full + 잔액 → 'MM/DD HH:mm · 잔액 N P'", () => {
    expect(pointLogMeta(makePointLog(), 'full')).toBe('11/07 18:02 · 잔액 1,240P');
  });

  it('full + balanceAfter null → 잔액 생략', () => {
    expect(pointLogMeta(makePointLog({ balanceAfter: null }), 'full')).toBe('11/07 18:02');
  });
});

describe('pointExpiryText', () => {
  it('1240 → 1,240P 소멸', () => {
    expect(pointExpiryText(1240)).toBe('1,240P 소멸');
  });

  it('0 → 0P 소멸', () => {
    expect(pointExpiryText(0)).toBe('0P 소멸');
  });
});

describe('withdrawErrorView', () => {
  it('CURRENT_PASSWORD_MISMATCH는 서버 문구 대신 C7 정본 문구를 비밀번호 칸에', () => {
    expect(
      withdrawErrorView({
        errorCode: 'CURRENT_PASSWORD_MISMATCH',
        message: '현재 비밀번호가 올바르지 않습니다.',
      }),
    ).toEqual({ field: 'password', message: WITHDRAW_PASSWORD_MISMATCH_MESSAGE });
    expect(WITHDRAW_PASSWORD_MISMATCH_MESSAGE).toBe('비밀번호가 일치하지 않습니다.');
  });
});
