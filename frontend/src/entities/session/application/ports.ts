export interface SessionStore {
  save(token: string): void;
  clear(): void;
  hasSession(): boolean;
  subscribe(listener: (hasSession: boolean) => void): () => void;
}
