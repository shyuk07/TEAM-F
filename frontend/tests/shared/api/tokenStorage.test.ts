import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { clearToken, onTokenChange, readToken, saveToken } from '@/shared/api/tokenStorage';

const KEY = 'lastcall.accessToken';

describe('tokenStorage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('저장한 토큰이 없으면 readToken은 null이다', () => {
    expect(readToken()).toBeNull();
  });

  it('saveToken은 lastcall.accessToken 키에 저장하고 readToken이 읽는다', () => {
    saveToken('abc');
    expect(localStorage.getItem(KEY)).toBe('abc');
    expect(readToken()).toBe('abc');
  });

  it('clearToken은 저장한 토큰을 지운다', () => {
    saveToken('abc');
    clearToken();
    expect(readToken()).toBeNull();
  });

  it('localStorage.getItem이 throw하면 readToken은 null을 돌려준다', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    expect(readToken()).toBeNull();
  });

  it('localStorage.setItem이 throw해도 saveToken은 예외를 던지지 않는다', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    expect(() => saveToken('abc')).not.toThrow();
  });

  it('localStorage.removeItem이 throw해도 clearToken은 예외를 던지지 않는다', () => {
    vi.spyOn(Storage.prototype, 'removeItem').mockImplementation(() => {
      throw new Error('blocked');
    });
    expect(() => clearToken()).not.toThrow();
  });

  it('onTokenChange: 같은 키의 storage 이벤트가 오면 현재 토큰으로 콜백을 부른다', () => {
    const cb = vi.fn();
    const off = onTokenChange(cb);
    localStorage.setItem(KEY, 'other-tab');
    window.dispatchEvent(new StorageEvent('storage', { key: KEY }));
    expect(cb).toHaveBeenCalledWith('other-tab');
    off();
  });

  it('onTokenChange: key가 null인 storage 이벤트(전체 삭제)에도 콜백을 부른다', () => {
    const cb = vi.fn();
    const off = onTokenChange(cb);
    window.dispatchEvent(new StorageEvent('storage', { key: null }));
    expect(cb).toHaveBeenCalledWith(null);
    off();
  });

  it('onTokenChange: 다른 키의 이벤트는 무시한다', () => {
    const cb = vi.fn();
    const off = onTokenChange(cb);
    window.dispatchEvent(new StorageEvent('storage', { key: 'other' }));
    expect(cb).not.toHaveBeenCalled();
    off();
  });

  it('onTokenChange가 돌려준 함수를 부르면 구독이 해제된다', () => {
    const cb = vi.fn();
    const off = onTokenChange(cb);
    off();
    window.dispatchEvent(new StorageEvent('storage', { key: KEY }));
    expect(cb).not.toHaveBeenCalled();
  });
});
