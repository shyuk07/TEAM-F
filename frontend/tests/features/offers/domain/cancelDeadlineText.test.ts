import { cancelDeadlineText, relativeDay } from '@/features/offers/domain/offerFormat';

// 표기는 브라우저 로컬 벽시계 기준(customer-home.md D-13)이라 로컬 생성자로 만든다.
// 로컬 생성자는 테스트 환경 TZ와 관계없이 같은 벽시계 값이 된다(tests/support/clock.ts와 같은 방식).
const NOW = new Date(2026, 10, 4, 17, 30);
const day = (d: number, h: number, m: number) => new Date(2026, 10, d, h, m);

describe('relativeDay', () => {
  it.each<[string, string, Date]>([
    ['같은 날', '오늘', day(4, 9, 0)],
    ['다음 날', '내일', day(5, 0, 0)],
    ['이틀 뒤', '11/06', day(6, 12, 0)],
  ])('%s → %s', (_name, text, d) => {
    expect(relativeDay(d, NOW)).toBe(text);
  });
});

describe('cancelDeadlineText', () => {
  it('같은 날 17:00 → 「오늘 17:00까지 (이후 취소 불가)」', () => {
    expect(cancelDeadlineText(day(4, 17, 0), NOW)).toBe('오늘 17:00까지 (이후 취소 불가)');
  });

  it('다음 날 09:05 → 「내일 09:05까지 (이후 취소 불가)」', () => {
    expect(cancelDeadlineText(day(5, 9, 5), NOW)).toBe('내일 09:05까지 (이후 취소 불가)');
  });

  it('이틀 뒤 → 「11/06 18:00까지 (이후 취소 불가)」', () => {
    expect(cancelDeadlineText(day(6, 18, 0), NOW)).toBe('11/06 18:00까지 (이후 취소 불가)');
  });

  it('이미 지난 시각도 같은 형식(D-7)', () => {
    expect(cancelDeadlineText(day(4, 16, 0), NOW)).toBe('오늘 16:00까지 (이후 취소 불가)');
  });
});
