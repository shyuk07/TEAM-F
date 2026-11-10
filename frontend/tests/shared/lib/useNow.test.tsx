import { act, renderHook } from '@testing-library/react';
import { useNow } from '@/shared/lib/useNow';

describe('useNow', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(2026, 10, 10, 17, 18, 0));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('처음 값은 현재 시각', () => {
    const { result } = renderHook(() => useNow(30_000));
    expect(result.current.getTime()).toBe(new Date(2026, 10, 10, 17, 18, 0).getTime());
  });

  it('intervalMs가 지날 때마다 갱신된다', () => {
    const { result } = renderHook(() => useNow(30_000));
    act(() => {
      vi.advanceTimersByTime(30_000);
    });
    expect(result.current.getTime()).toBe(new Date(2026, 10, 10, 17, 18, 30).getTime());
    act(() => {
      vi.advanceTimersByTime(30_000);
    });
    expect(result.current.getTime()).toBe(new Date(2026, 10, 10, 17, 19, 0).getTime());
  });

  it('언마운트하면 타이머를 정리한다', () => {
    const { unmount } = renderHook(() => useNow(30_000));
    expect(vi.getTimerCount()).toBeGreaterThan(0);
    unmount();
    expect(vi.getTimerCount()).toBe(0);
  });
});
