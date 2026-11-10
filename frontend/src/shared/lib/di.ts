import { createContext, useContext } from 'react';

export type Token<T> = { readonly key: symbol; readonly name: string; readonly _type?: T };
export function createToken<T>(name: string): Token<T> {
  return { key: Symbol(name), name };
}

export type Binding = { readonly token: Token<unknown>; readonly value: unknown };
export function bind<T>(token: Token<T>, value: T): Binding {
  return { token, value };
}

export class Container {
  private readonly map = new Map<symbol, unknown>();
  constructor(bindings: readonly Binding[]) {
    for (const b of bindings) {
      if (this.map.has(b.token.key)) {
        throw new Error(`의존성 중복 등록: ${b.token.name} (토큰은 소유 영역 한 곳에서만 등록)`);
      }
      this.map.set(b.token.key, b.value);
    }
  }
  get<T>(token: Token<T>): T {
    if (!this.map.has(token.key)) {
      throw new Error(
        `의존성 미등록: ${token.name} (소유 영역의 wiring.ts와 app/container.ts 확인)`,
      );
    }
    return this.map.get(token.key) as T;
  }
}

export const DepsContext = createContext<Container | null>(null);

export function useDep<T>(token: Token<T>): T {
  const container = useContext(DepsContext);
  if (!container) throw new Error('DepsProvider 밖에서 useDep를 호출했습니다.');
  return container.get(token);
}
