import { afterEach, beforeEach, vi } from 'vitest';

// jsdom에는 URL.createObjectURL·revokeObjectURL이 없다. 호출마다 blob:preview-N을 돌려주는 가짜를 둔다.
export function useFakeObjectUrl() {
  const create = vi.fn<(obj: Blob | MediaSource) => string>();
  const revoke = vi.fn<(url: string) => void>();
  let n = 0;
  const original = { create: URL.createObjectURL, revoke: URL.revokeObjectURL };

  beforeEach(() => {
    n = 0;
    create.mockReset();
    revoke.mockReset();
    create.mockImplementation(() => `blob:preview-${++n}`);
    Object.defineProperty(URL, 'createObjectURL', {
      value: create,
      configurable: true,
      writable: true,
    });
    Object.defineProperty(URL, 'revokeObjectURL', {
      value: revoke,
      configurable: true,
      writable: true,
    });
  });

  afterEach(() => {
    Object.defineProperty(URL, 'createObjectURL', {
      value: original.create,
      configurable: true,
      writable: true,
    });
    Object.defineProperty(URL, 'revokeObjectURL', {
      value: original.revoke,
      configurable: true,
      writable: true,
    });
  });

  return { create, revoke };
}

export function makeFile(type: string, bytes: number, name = 'photo'): File {
  return new File([new Uint8Array(bytes)], name, { type });
}
