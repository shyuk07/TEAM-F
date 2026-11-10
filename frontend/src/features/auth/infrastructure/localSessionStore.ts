import type { SessionStore } from '@/entities/session';

export class LocalSessionStore implements SessionStore {
  save(token: string): void {
    void token;
    throw new Error('not implemented: LocalSessionStore.save');
  }

  clear(): void {
    throw new Error('not implemented: LocalSessionStore.clear');
  }

  hasSession(): boolean {
    throw new Error('not implemented: LocalSessionStore.hasSession');
  }

  subscribe(listener: (hasSession: boolean) => void): () => void {
    void listener;
    throw new Error('not implemented: LocalSessionStore.subscribe');
  }
}
