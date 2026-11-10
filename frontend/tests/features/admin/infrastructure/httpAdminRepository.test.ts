import { HttpAdminRepository } from '@/features/admin/infrastructure/httpAdminRepository';

const { request } = vi.hoisted(() => ({ request: vi.fn() }));

vi.mock('@/shared/api/client', () => ({
  request,
  apiGet: (path: string, signal?: AbortSignal) => request(path, { signal }),
  apiPost: (path: string, body?: unknown, signal?: AbortSignal) =>
    request(path, { method: 'POST', body, signal }),
}));

function lastCall(): {
  path: string;
  opts: { method?: string; body?: unknown; signal?: AbortSignal };
} {
  const call = request.mock.calls.at(-1) ?? [];
  return { path: call[0] as string, opts: (call[1] ?? {}) as { method?: string; body?: unknown } };
}

const ID = '11111111-1111-4111-8111-111111111111';

describe('HttpAdminRepository', () => {
  const repo = new HttpAdminRepository();

  beforeEach(() => {
    request.mockReset();
  });

  it('listUsers: 비어 있지 않은 필터만 쿼리에 넣고 응답을 변환한다', async () => {
    request.mockResolvedValue({
      items: [
        {
          id: ID,
          email: 'owner1@example.com',
          name: null,
          role: 'OWNER',
          status: 'PENDING',
          created_at: '2026-11-08T01:00:00Z',
        },
      ],
      page: 2,
      size: 20,
      total: 21,
    });
    const ctrl = new AbortController();
    const page = await repo.listUsers(
      { role: 'OWNER', status: 'PENDING', email: 'a@b', page: 2, size: 20 },
      ctrl.signal,
    );
    const { path, opts } = lastCall();
    expect(path).toBe('/v1/admin/users?role=OWNER&status=PENDING&email=a%40b&page=2&size=20');
    expect(opts.signal).toBe(ctrl.signal);
    expect(page).toEqual({
      items: [
        {
          id: ID,
          email: 'owner1@example.com',
          name: null,
          role: 'OWNER',
          status: 'PENDING',
          createdAt: new Date('2026-11-08T01:00:00Z'),
        },
      ],
      page: 2,
      size: 20,
      total: 21,
    });
  });

  it('listUsers: 필터가 없으면 page·size만', async () => {
    request.mockResolvedValue({ items: [], page: 1, size: 20, total: 0 });
    await repo.listUsers({ page: 1, size: 20 });
    expect(lastCall().path).toBe('/v1/admin/users?page=1&size=20');
  });

  it('findUser: users_point를 point로', async () => {
    request.mockResolvedValue({
      id: ID,
      email: 'c@x',
      name: '박고객',
      phone: '010-1234-5678',
      role: 'CUSTOMER',
      users_point: 2300,
      created_at: '2026-10-21T00:00:00Z',
      status: 'APPROVED',
    });
    const u = await repo.findUser(ID);
    expect(lastCall().path).toBe(`/v1/admin/users/${ID}`);
    expect(u.point).toBe(2300);
    expect(u.phone).toBe('010-1234-5678');
  });

  it('findUserPoints: history를 entries로, 날짜 변환', async () => {
    request.mockResolvedValue({
      user_id: ID,
      balance: 2300,
      history: [
        {
          id: 'p1',
          amount: -500,
          type: 'USE',
          reason: null,
          balance_after: null,
          created_by: null,
          created_at: null,
        },
      ],
      page: 1,
      size: 5,
      total: 1,
    });
    const h = await repo.findUserPoints(ID, 1, 5);
    expect(lastCall().path).toBe(`/v1/admin/users/${ID}/points?page=1&size=5`);
    expect(h.balance).toBe(2300);
    expect(h.entries).toEqual([
      { id: 'p1', amount: -500, type: 'USE', reason: null, balanceAfter: null, createdAt: null },
    ]);
  });

  it.each([
    [
      'approveOwner',
      () => repo.approveOwner(ID),
      `/v1/admin/owners/${ID}/approve`,
      'PATCH',
      undefined,
    ],
    [
      'rejectOwner',
      () => repo.rejectOwner(ID, '서류 불일치'),
      `/v1/admin/owners/${ID}/reject`,
      'PATCH',
      { reason: '서류 불일치' },
    ],
    [
      'suspendUser 무기한',
      () => repo.suspendUser(ID, '노쇼', null),
      `/v1/admin/users/${ID}/suspend`,
      'PATCH',
      { reason: '노쇼', suspended_until: null },
    ],
    [
      'suspendUser 기한',
      () => repo.suspendUser(ID, '노쇼', new Date('2026-11-30T14:59:59.999Z')),
      `/v1/admin/users/${ID}/suspend`,
      'PATCH',
      { reason: '노쇼', suspended_until: '2026-11-30T14:59:59.999Z' },
    ],
    [
      'grantPoints',
      () => repo.grantPoints(ID, 1000, '보상'),
      `/v1/admin/users/${ID}/points`,
      'POST',
      { amount: 1000, reason: '보상' },
    ],
  ])('%s', async (_name, call, path, method, body) => {
    request.mockResolvedValue({ balance_after: 3300 });
    await call();
    expect(lastCall()).toEqual({ path, opts: body === undefined ? { method } : { method, body } });
  });

  it('withdrawUser: DELETE + 본문 사유, 취소 예약 수를 돌려준다', async () => {
    request.mockResolvedValue({
      id: ID,
      status: 'WITHDRAWN',
      deleted_at: null,
      cancelled_reservation_count: 2,
    });
    await expect(repo.withdrawUser(ID, '사기')).resolves.toEqual({ cancelledReservationCount: 2 });
    expect(lastCall()).toEqual({
      path: `/v1/admin/users/${ID}`,
      opts: { method: 'DELETE', body: { reason: '사기' } },
    });
  });

  it('상점 정지·폐점, 할인 정지: 이름·상태를 돌려준다', async () => {
    request.mockResolvedValue({
      id: 's1',
      owner_id: 'o',
      name: '망원베이커리',
      status: 'SUSPENDED',
    });
    await expect(repo.suspendStore('s1', 'x')).resolves.toEqual({
      id: 's1',
      name: '망원베이커리',
      status: 'SUSPENDED',
    });
    expect(lastCall().path).toBe('/v1/admin/stores/s1/suspend');

    request.mockResolvedValue({ id: 's1', owner_id: 'o', name: '망원베이커리', status: 'CLOSED' });
    await repo.closeStore('s1', 'x');
    expect(lastCall().path).toBe('/v1/admin/stores/s1/close');

    request.mockResolvedValue({ id: 'o1', store_id: 's1', title: '식빵', status: 'SUSPENDED' });
    await expect(repo.suspendOffer('o1', 'x')).resolves.toEqual({
      id: 'o1',
      title: '식빵',
      status: 'SUSPENDED',
    });
    expect(lastCall()).toEqual({
      path: '/v1/admin/offers/o1/suspend',
      opts: { method: 'PATCH', body: { reason: 'x' } },
    });
  });
});
