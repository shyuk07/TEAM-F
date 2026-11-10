import {
  formatDate,
  formatQuantity,
  formatTime,
  formatTimeRange,
  formatWon,
} from '@/features/reservations/domain/format';

describe('format', () => {
  it.each([
    [11500, '11,500원'],
    [0, '0원'],
  ])('formatWon(%i) → %s', (n, expected) => {
    expect(formatWon(n)).toBe(expected);
  });

  it('formatTimeRange는 en dash(U+2013)로 잇는다', () => {
    expect(
      formatTimeRange(new Date('2026-11-10T18:00:00+09:00'), new Date('2026-11-10T20:00:00+09:00')),
    ).toBe('18:00–20:00');
  });

  it('formatDate는 MM/DD', () => {
    expect(formatDate(new Date('2026-11-07T12:00:00+09:00'))).toBe('11/07');
  });

  it.each([
    [new Date('2026-11-10T17:00:00+09:00'), '17:00'],
    [new Date('2026-11-10T09:05:00+09:00'), '09:05'],
  ])('formatTime은 24시간 HH:mm (%s → %s)', (d, expected) => {
    expect(formatTime(d)).toBe(expected);
  });

  it('formatQuantity는 「이름 × 수량」', () => {
    expect(formatQuantity('식빵 모둠', 2)).toBe('식빵 모둠 × 2');
  });
});
