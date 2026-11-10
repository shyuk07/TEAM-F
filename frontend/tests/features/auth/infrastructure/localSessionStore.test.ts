import { LocalSessionStore } from '@/features/auth/infrastructure/localSessionStore';

const KEY = 'lastcall.accessToken';

function storageEvent(key: string | null) {
  window.dispatchEvent(new StorageEvent('storage', { key }));
}

describe('LocalSessionStore', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('처음에는 hasSession()이 false다', () => {
    expect(new LocalSessionStore().hasSession()).toBe(false);
  });

  it('save() 뒤 hasSession()이 true이고 localStorage에 토큰이 있다', () => {
    const store = new LocalSessionStore();
    store.save('t');
    expect(store.hasSession()).toBe(true);
    expect(localStorage.getItem(KEY)).toBe('t');
  });

  it('clear() 뒤 hasSession()이 false다', () => {
    const store = new LocalSessionStore();
    store.save('t');
    store.clear();
    expect(store.hasSession()).toBe(false);
    expect(localStorage.getItem(KEY)).toBeNull();
  });

  describe('subscribe', () => {
    it('같은 탭 clear()는 리스너를 false로 한 번 부른다', () => {
      const store = new LocalSessionStore();
      store.save('t');
      const listener = vi.fn();
      store.subscribe(listener);
      store.clear();
      expect(listener).toHaveBeenCalledTimes(1);
      expect(listener).toHaveBeenCalledWith(false);
    });

    it('같은 탭 save()는 리스너를 부르지 않는다', () => {
      const store = new LocalSessionStore();
      const listener = vi.fn();
      store.subscribe(listener);
      store.save('t');
      expect(listener).not.toHaveBeenCalled();
    });

    it('토큰 키의 StorageEvent(값 있음)는 리스너를 true로 부른다', () => {
      const store = new LocalSessionStore();
      const listener = vi.fn();
      store.subscribe(listener);
      localStorage.setItem(KEY, 'other-tab');
      storageEvent(KEY);
      expect(listener).toHaveBeenCalledWith(true);
    });

    it('다른 key의 StorageEvent는 무시한다', () => {
      const store = new LocalSessionStore();
      const listener = vi.fn();
      store.subscribe(listener);
      localStorage.setItem('other', 'x');
      storageEvent('other');
      expect(listener).not.toHaveBeenCalled();
    });

    it('구독을 해제하면 이후 이벤트에 불리지 않는다', () => {
      const store = new LocalSessionStore();
      const listener = vi.fn();
      const unsubscribe = store.subscribe(listener);
      unsubscribe();
      localStorage.setItem(KEY, 'other-tab');
      storageEvent(KEY);
      store.clear();
      expect(listener).not.toHaveBeenCalled();
    });
  });
});
