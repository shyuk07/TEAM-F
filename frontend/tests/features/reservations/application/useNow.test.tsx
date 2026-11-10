import { act, renderHook } from '@testing-library/react';
import { useNow } from '@/features/reservations/application/useNow';
import { at } from '../fakes/reservations';

describe('useNow', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(at(16));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('현재 시각을 돌려주고 주기마다 갱신한다', () => {
    const { result } = renderHook(() => useNow(1000));
    expect(result.current.getTime()).toBe(at(16).getTime());
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(result.current.getTime()).toBe(at(16, 0, 1).getTime());
  });

  it('언마운트하면 타이머를 정리한다', () => {
    const { unmount } = renderHook(() => useNow(1000));
    unmount();
    expect(vi.getTimerCount()).toBe(0);
  });
});
