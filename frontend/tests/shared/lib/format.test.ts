import { formatHm, formatMd, groupDigits, isSameLocalDate } from '@/shared/lib/format';
import { at } from '../../support/clock';

describe('groupDigits', () => {
  it.each<[number, string]>([
    [0, '0'],
    [1240, '1,240'],
    [1000000, '1,000,000'],
    [-500, '-500'],
  ])('%d → %s', (n, expected) => {
    expect(groupDigits(n)).toBe(expected);
  });
});

describe('formatHm·formatMd', () => {
  it('formatHm은 24시간 HH:mm, 두 자리 0 채움', () => {
    expect(formatHm(at(10, 9, 5))).toBe('09:05');
  });

  it('formatMd는 MM/DD', () => {
    expect(formatMd(at(7, 18, 2))).toBe('11/07');
  });
});

describe('isSameLocalDate', () => {
  it('23:59와 다음 날 00:00은 다른 날이다', () => {
    expect(isSameLocalDate(at(10, 23, 59), at(11, 0, 0))).toBe(false);
  });

  it('같은 날 00:00과 23:59는 같은 날이다', () => {
    expect(isSameLocalDate(at(10, 0, 0), at(10, 23, 59))).toBe(true);
  });
});
