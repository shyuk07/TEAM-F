import { HttpReservationRepository } from '@/features/reservations/infrastructure/httpReservationRepository';
import { ApiError } from '@/shared/api/error';

const { request } = vi.hoisted(() => ({ request: vi.fn() }));

// apiGet·apiPost는 실제 client처럼 request를 거치게 해서, 구현이 무엇을 쓰든 request 호출로 확인한다.
vi.mock('@/shared/api/client', () => ({
  request,
  apiGet: (path: string, signal?: AbortSignal) => request(path, { signal }),
  apiPost: (path: string, body?: unknown, signal?: AbortSignal) =>
    request(path, { method: 'POST', body, signal }),
}));

const itemDto = {
  id: 'r1',
  offer_id: 'o1',
  store_name: '망원베이커리',
  product_name: '식빵 모둠',
  quantity: 2,
  total_price: 11500,
  status: 'RESERVED',
  created_at: '2026-11-10T15:30:00+09:00',
  cancelled_by: null,
  pickup_code: 'A12345',
  pickup_address: '서울 마포구 망원로 1',
  pickup_start: '2026-11-10T18:00:00+09:00',
  pickup_end: '2026-11-10T20:00:00+09:00',
  cancellable_until: '2026-11-10T17:00:00+09:00',
};

const expectedItem = {
  id: 'r1',
  offerId: 'o1',
  storeName: '망원베이커리',
  productName: '식빵 모둠',
  quantity: 2,
  totalPrice: 11500,
  status: 'RESERVED',
  createdAt: new Date('2026-11-10T15:30:00+09:00'),
  cancelledBy: null,
  pickupCode: 'A12345',
  pickupAddress: '서울 마포구 망원로 1',
  pickupStart: new Date('2026-11-10T18:00:00+09:00'),
  pickupEnd: new Date('2026-11-10T20:00:00+09:00'),
  cancellableUntil: new Date('2026-11-10T17:00:00+09:00'),
};

function lastPath(): string {
  return String(request.mock.calls.at(-1)?.[0]);
}

function lastOptions(): { method?: string; body?: unknown; signal?: AbortSignal } {
  return (request.mock.calls.at(-1)?.[1] ?? {}) as ReturnType<typeof lastOptions>;
}

function lastQuery(): URLSearchParams {
  return new URL(lastPath(), 'http://x').searchParams;
}

describe('HttpReservationRepository', () => {
  const repo = new HttpReservationRepository();

  beforeEach(() => {
    request.mockReset();
  });

  describe('create', () => {
    const createdDto = {
      id: 'r-new',
      user_id: 'u1',
      offer_id: 'o1',
      quantity: 2,
      unit_price: 3000,
      total_price: 6000,
      status: 'PENDING_PAYMENT',
      created_at: '2026-11-10T15:00:00+09:00',
      store_name: '마감 베이커리',
      product_name: '샌드위치',
    };

    it('/v1/reservations에 {offer_id, quantity}를 POST한다', async () => {
      request.mockResolvedValue(createdDto);
      await repo.create({ offerId: 'o1', quantity: 2 });
      expect(lastPath()).toBe('/v1/reservations');
      expect(lastOptions()).toMatchObject({
        method: 'POST',
        body: { offer_id: 'o1', quantity: 2 },
      });
    });

    it('201 응답을 camelCase·Date로 바꾸고 user_id는 버린다', async () => {
      request.mockResolvedValue(createdDto);
      const result = await repo.create({ offerId: 'o1', quantity: 2 });
      expect(result).toEqual({
        id: 'r-new',
        offerId: 'o1',
        quantity: 2,
        unitPrice: 3000,
        totalPrice: 6000,
        status: 'PENDING_PAYMENT',
        createdAt: new Date('2026-11-10T15:00:00+09:00'),
        storeName: '마감 베이커리',
        productName: '샌드위치',
      });
    });

    it('409 PENDING_RESERVATION_EXISTS ApiError를 그대로 올린다', async () => {
      const err = new ApiError(409, 'PENDING_RESERVATION_EXISTS', '이미 있습니다.');
      request.mockRejectedValue(err);
      await expect(repo.create({ offerId: 'o1', quantity: 1 })).rejects.toBe(err);
    });
  });

  describe('listMine', () => {
    it('status가 없으면 쿼리에 page·size만 넣는다', async () => {
      request.mockResolvedValue({ reservations: [], page: 1, size: 100, total: 0 });
      await repo.listMine({ page: 1, size: 100 });
      expect(new URL(lastPath(), 'http://x').pathname).toBe('/v1/users/me/reservations');
      const q = lastQuery();
      expect(q.get('page')).toBe('1');
      expect(q.get('size')).toBe('100');
      expect(q.has('status')).toBe(false);
    });

    it('status가 있으면 쿼리에 포함한다', async () => {
      request.mockResolvedValue({ reservations: [], page: 1, size: 100, total: 0 });
      await repo.listMine({ status: 'PENDING_PAYMENT', page: 2, size: 100 });
      expect(lastQuery().get('status')).toBe('PENDING_PAYMENT');
      expect(lastQuery().get('page')).toBe('2');
    });

    it('14필드를 Reservation으로 바꾸고 page·size·total을 그대로 둔다', async () => {
      request.mockResolvedValue({ reservations: [itemDto], page: 1, size: 100, total: 1 });
      const result = await repo.listMine({ page: 1, size: 100 });
      expect(result).toEqual({ items: [expectedItem], page: 1, size: 100, total: 1 });
    });

    it('signal을 request에 넘긴다', async () => {
      request.mockResolvedValue({ reservations: [], page: 1, size: 100, total: 0 });
      const ctrl = new AbortController();
      await repo.listMine({ page: 1, size: 100 }, ctrl.signal);
      expect(lastOptions().signal).toBe(ctrl.signal);
    });

    it('알 수 없는 status 문자열이면 reject한다', async () => {
      request.mockResolvedValue({
        reservations: [{ ...itemDto, status: 'WEIRD' }],
        page: 1,
        size: 100,
        total: 1,
      });
      await expect(repo.listMine({ page: 1, size: 100 })).rejects.toThrow();
    });

    it('알 수 없는 cancelled_by 문자열이면 reject한다', async () => {
      request.mockResolvedValue({
        reservations: [{ ...itemDto, status: 'CANCELLED', cancelled_by: 'ALIEN' }],
        page: 1,
        size: 100,
        total: 1,
      });
      await expect(repo.listMine({ page: 1, size: 100 })).rejects.toThrow();
    });
  });

  describe('get', () => {
    it('GET /v1/reservations/{id}로 한 건을 Reservation으로 바꾼다', async () => {
      request.mockResolvedValue(itemDto);
      const result = await repo.get('r1');
      expect(lastPath()).toBe('/v1/reservations/r1');
      expect(lastOptions().method ?? 'GET').toBe('GET');
      expect(result).toEqual(expectedItem);
    });

    it('id를 encodeURIComponent한다', async () => {
      request.mockResolvedValue(itemDto);
      await repo.get('a/b?c');
      expect(lastPath()).toBe(`/v1/reservations/${encodeURIComponent('a/b?c')}`);
    });

    it('404 ApiError를 그대로 올린다', async () => {
      const err = new ApiError(404, 'NOT_FOUND', '예약 정보 없음');
      request.mockRejectedValue(err);
      await expect(repo.get('r1')).rejects.toBe(err);
    });
  });

  describe('cancel', () => {
    it('POST /v1/reservations/{id}/cancel 후 cancelled_by를 매핑한다', async () => {
      request.mockResolvedValue({
        id: 'r1',
        status: 'CANCELLED',
        cancelled_at: '2026-11-10T16:00:00+09:00',
        cancelled_by: 'CUSTOMER',
      });
      const result = await repo.cancel('r1');
      expect(lastPath()).toBe('/v1/reservations/r1/cancel');
      expect(lastOptions().method).toBe('POST');
      expect(result).toEqual({ id: 'r1', status: 'CANCELLED', cancelledBy: 'CUSTOMER' });
    });

    it('id를 encodeURIComponent한다', async () => {
      request.mockResolvedValue({ id: 'a/b', status: 'CANCELLED', cancelled_by: 'CUSTOMER' });
      await repo.cancel('a/b');
      expect(lastPath()).toBe(`/v1/reservations/${encodeURIComponent('a/b')}/cancel`);
    });

    it('400 CANCELLATION_DEADLINE_PASSED ApiError를 그대로 올린다', async () => {
      const err = new ApiError(400, 'CANCELLATION_DEADLINE_PASSED', '마감');
      request.mockRejectedValue(err);
      await expect(repo.cancel('r1')).rejects.toBe(err);
    });
  });
});
