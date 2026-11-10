import { beforeEach, describe, expect, it, vi } from 'vitest';
import { HttpStoreCommands } from '@/features/stores/infrastructure/httpStoreCommands';
import { request } from '@/shared/api/client';

vi.mock('@/shared/api/client', () => ({ apiGet: vi.fn(), request: vi.fn() }));

const dto = {
  id: 'st-1',
  owner_id: 'u-owner',
  name: '망원베이커리',
  pickup_address: '서울시 마포구 망원로 10',
  latitude: 37.55,
  longitude: 126.9,
  created_at: '2026-01-02T03:04:05Z',
  approval_at: null,
  closed_at: null,
};

describe('features/stores infrastructure HttpStoreCommands.open', () => {
  const requestMock = vi.mocked(request);

  beforeEach(() => {
    requestMock.mockReset();
  });

  it('POST /v1/stores에 body { pickup_address }를 보내고 Store로 바꾼다', async () => {
    requestMock.mockResolvedValue(dto);
    const ctrl = new AbortController();
    const store = await new HttpStoreCommands().open('서울 마포구', ctrl.signal);
    expect(requestMock).toHaveBeenCalledWith('/v1/stores', {
      method: 'POST',
      body: { pickup_address: '서울 마포구' },
      signal: ctrl.signal,
    });
    expect(store.status).toBe('ACTIVE');
    expect(store.latitude).toBe(37.55);
    expect(store.longitude).toBe(126.9);
    expect(store.createdAt).toEqual(new Date('2026-01-02T03:04:05Z'));
  });

  it('close는 /v1/stores/{id}/close 경로를 인코딩해 POST하고 본문 없이 undefined를 돌려준다', async () => {
    requestMock.mockResolvedValue({ id: 'a/b', name: '망원베이커리', closed_at: 'z' });
    await expect(new HttpStoreCommands().close('a/b')).resolves.toBeUndefined();
    expect(requestMock).toHaveBeenCalledWith('/v1/stores/a%2Fb/close', {
      method: 'POST',
      signal: undefined,
    });
  });

  it('오류는 그대로 던진다(변환하지 않는다)', async () => {
    const err = new Error('boom');
    requestMock.mockRejectedValue(err);
    await expect(new HttpStoreCommands().open('서울')).rejects.toBe(err);
    await expect(new HttpStoreCommands().close('st-1')).rejects.toBe(err);
  });
});
