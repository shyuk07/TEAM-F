import { vi } from 'vitest';

// 고정 시각: 2026-11-10 17:18 (로컬). 로컬 생성자로 만들어 테스트 환경 TZ와 관계없이 같은 벽시계 값이 된다.
export const NOW = new Date(2026, 10, 10, 17, 18, 0);

/** 로컬 벽시계 시각(2026년 11월 day일 h:m). */
export function at(day: number, h: number, m: number, s = 0): Date {
  return new Date(2026, 10, day, h, m, s);
}

/** Date만 가짜로 바꾼다(setTimeout·setInterval은 실제 타이머라 waitFor·userEvent가 그대로 동작). */
export function fixNow(now: Date = NOW): void {
  vi.useFakeTimers({ now, toFake: ['Date'] });
}

export function restoreNow(): void {
  vi.useRealTimers();
}
