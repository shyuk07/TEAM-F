import { renderHook } from '@testing-library/react';
import type { ReactNode } from 'react';
import { describe, expect, it } from 'vitest';
import { bind, Container, createToken, useDep } from '@/shared/lib/di';
import { DepsProvider } from '@/shared/lib/DepsProvider';

interface Greeter {
  hello(): string;
}
const GreeterToken = createToken<Greeter>('Greeter');
const OtherToken = createToken<number>('Other');

describe('createToken / bind', () => {
  it('같은 이름이어도 토큰마다 key가 다르다', () => {
    const a = createToken<number>('Same');
    const b = createToken<number>('Same');
    expect(a.name).toBe('Same');
    expect(a.key).not.toBe(b.key);
  });

  it('bind는 토큰과 값을 묶는다', () => {
    const b = bind(OtherToken, 3);
    expect(b.token).toBe(OtherToken);
    expect(b.value).toBe(3);
  });
});

describe('Container', () => {
  it('등록한 값을 토큰으로 조회한다', () => {
    const impl: Greeter = { hello: () => 'hi' };
    const c = new Container([bind(GreeterToken, impl), bind(OtherToken, 7)]);
    expect(c.get(GreeterToken)).toBe(impl);
    expect(c.get(OtherToken)).toBe(7);
  });

  it('미등록 토큰을 조회하면 "의존성 미등록: <이름>" 오류를 던진다', () => {
    const c = new Container([]);
    expect(() => c.get(GreeterToken)).toThrow('의존성 미등록: Greeter');
  });

  it('같은 토큰을 두 번 등록하면 "의존성 중복 등록: <이름>" 오류를 던진다', () => {
    expect(() => new Container([bind(OtherToken, 1), bind(OtherToken, 2)])).toThrow(
      '의존성 중복 등록: Other',
    );
  });
});

describe('DepsProvider / useDep', () => {
  it('Provider 안에서 토큰으로 값을 꺼낸다', () => {
    const impl: Greeter = { hello: () => 'hi' };
    const container = new Container([bind(GreeterToken, impl)]);
    const wrapper = ({ children }: { children: ReactNode }) => (
      <DepsProvider container={container}>{children}</DepsProvider>
    );
    const { result } = renderHook(() => useDep(GreeterToken), { wrapper });
    expect(result.current).toBe(impl);
  });

  it('DepsProvider 밖에서 호출하면 오류를 던진다', () => {
    expect(() => renderHook(() => useDep(GreeterToken))).toThrow(
      'DepsProvider 밖에서 useDep를 호출했습니다.',
    );
  });

  it('Provider 안이라도 미등록 토큰이면 "의존성 미등록" 오류를 던진다', () => {
    const wrapper = ({ children }: { children: ReactNode }) => (
      <DepsProvider container={new Container([])}>{children}</DepsProvider>
    );
    expect(() => renderHook(() => useDep(GreeterToken), { wrapper })).toThrow(
      '의존성 미등록: Greeter',
    );
  });
});
