import type { SessionStore } from '@/entities/session';
import { clearToken, onTokenChange, readToken, saveToken } from '@/shared/api/tokenStorage';

type Listener = (hasSession: boolean) => void;

export class LocalSessionStore implements SessionStore {
  private readonly listeners = new Set<Listener>();
  private stopWatching: (() => void) | null = null;

  save(token: string): void {
    saveToken(token);
  }

  clear(): void {
    clearToken();
    this.notify(false);
  }

  hasSession(): boolean {
    return readToken() !== null;
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    // 다른 탭의 변경 감시는 한 번만 건다.
    this.stopWatching ??= onTokenChange((token) => this.notify(token !== null));
    return () => {
      this.listeners.delete(listener);
      if (this.listeners.size === 0) {
        this.stopWatching?.();
        this.stopWatching = null;
      }
    };
  }

  private notify(has: boolean): void {
    for (const l of [...this.listeners]) l(has);
  }
}
