import { vi } from 'vitest';
import type { SessionStore } from '@/entities/session';

type Listener = (hasSession: boolean) => void;

// subscribe 계약(auth.md §2.1): 같은 탭 clear()와 다른 탭 변경(emit)만 통지하고, 같은 탭 save()는 통지하지 않는다.
export class FakeSessionStore implements SessionStore {
  private has: boolean;
  private readonly listeners = new Set<Listener>();

  constructor(initial = false) {
    this.has = initial;
  }

  save = vi.fn((token: string): void => {
    void token;
    this.has = true;
  });

  clear = vi.fn((): void => {
    this.has = false;
    this.notify(false);
  });

  hasSession = vi.fn((): boolean => this.has);

  subscribe = vi.fn((listener: Listener): (() => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  });

  /** 다른 탭에서 세션이 바뀐 것처럼 구독자를 부른다. */
  emit(has: boolean): void {
    this.has = has;
    this.notify(has);
  }

  private notify(has: boolean): void {
    for (const l of [...this.listeners]) l(has);
  }
}
