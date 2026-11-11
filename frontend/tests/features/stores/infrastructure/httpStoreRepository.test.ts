import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError } from '@/shared/api/error';
import { HttpStoreRepository } from '@/features/stores/infrastructure/httpStoreRepository';
import { apiGet } from '@/shared/api/client';

vi.mock('@/shared/api/client', () => ({ apiGet: vi.fn(), request: vi.fn() }));

const dto = {
  id: 'st-1',
  owner_id: 'u-owner',
  name: '망원베이커리',
  pickup_address: '서울시 마포구 망원로 10',
  latitude: null,
  longitude: null,
  created_at: '2026-01-02T03:04:05Z',
  approval_at: '2026-01-03T00:00:00Z',
  closed_at: null,
  status: 'ACTIVE',
};

describe('features/stores infrastructure HttpStoreRepository.findMine', () => {
  const apiGetMock = vi.mocked(apiGet);

  beforeEach(() => {
    apiGetMock.mockReset();
  });

  it('/v1/stores/me를 apiGet으로 호출한다', async () => {
    apiGetMock.mockResolvedValue(dto);
    await new HttpStoreRepository().findMine();
    expect(apiGetMock).toHaveBeenCalledWith('/v1/stores/me', undefined);
  });

  it('DTO를 Store로 바꾼다(createdAt은 Date, 좌표는 null)', async () => {
    apiGetMock.mockResolvedValue(dto);
    const store = await new HttpStoreRepository().findMine();
    expect(store).toEqual({
      id: 'st-1',
      ownerId: 'u-owner',
      name: '망원베이커리',
      pickupAddress: '서울시 마포구 망원로 10',
      latitude: null,
      longitude: null,
      createdAt: new Date('2026-01-02T03:04:05Z'),
      approvalAt: new Date('2026-01-03T00:00:00Z'),
      closedAt: null,
      status: 'ACTIVE',
    });
    expect(store?.createdAt).toBeInstanceOf(Date);
  });

  it('closed_at이 문자열로 오면 closedAt은 Date이고 status는 CLOSED다', async () => {
    apiGetMock.mockResolvedValue({ ...dto, closed_at: '2026-02-01T09:00:00Z', status: 'CLOSED' });
    const store = await new HttpStoreRepository().findMine();
    expect(store?.closedAt).toEqual(new Date('2026-02-01T09:00:00Z'));
    expect(store?.status).toBe('CLOSED');
  });

  it('ApiError(404, NOT_FOUND)는 null을 돌려준다', async () => {
    apiGetMock.mockRejectedValue(new ApiError(404, 'NOT_FOUND', '상점이 없습니다'));
    await expect(new HttpStoreRepository().findMine()).resolves.toBeNull();
  });

  it('404라도 errorCode가 다르면 던진다', async () => {
    apiGetMock.mockRejectedValue(new ApiError(404, 'UNKNOWN', 'x'));
    await expect(new HttpStoreRepository().findMine()).rejects.toMatchObject({
      errorCode: 'UNKNOWN',
    });
  });

  it.each([
    [401, 'UNAUTHORIZED'],
    [403, 'FORBIDDEN'],
    [0, 'NETWORK_ERROR'],
  ])('ApiError(%i, %s)는 그대로 던진다', async (status, errorCode) => {
    apiGetMock.mockRejectedValue(new ApiError(status, errorCode, 'x'));
    await expect(new HttpStoreRepository().findMine()).rejects.toMatchObject({ errorCode });
  });

  it('알 수 없는 status 값이면 Error를 던진다', async () => {
    apiGetMock.mockResolvedValue({ ...dto, status: 'PAUSED' });
    await expect(new HttpStoreRepository().findMine()).rejects.toThrow(/status/);
  });
});
