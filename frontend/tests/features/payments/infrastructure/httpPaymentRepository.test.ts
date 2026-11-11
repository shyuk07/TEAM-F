import { HttpPaymentRepository } from '@/features/payments/infrastructure/httpPaymentRepository';
import { ApiError } from '@/shared/api/error';

const { request } = vi.hoisted(() => ({ request: vi.fn() }));

vi.mock('@/shared/api/client', () => ({
  request,
  apiGet: (path: string, signal?: AbortSignal) => request(path, { signal }),
  apiPost: (path: string, body?: unknown, signal?: AbortSignal) =>
    request(path, { method: 'POST', body, signal }),
}));

const paymentDto = {
  id: 'p1',
  reservation_id: 'r1',
  amount: 11000,
  status: 'PAID',
  paid_at: '2026-11-10T15:00:00+09:00',
};

describe('HttpPaymentRepository', () => {
  const repo = new HttpPaymentRepository();

  beforeEach(() => {
    request.mockReset();
  });

  it('/v1/payments에 {reservation_id, use_point}를 POST한다', async () => {
    request.mockResolvedValue(paymentDto);
    await repo.pay({ reservationId: 'r1', usePoint: 500 });
    expect(request.mock.calls.at(-1)?.[0]).toBe('/v1/payments');
    expect(request.mock.calls.at(-1)?.[1]).toMatchObject({
      method: 'POST',
      body: { reservation_id: 'r1', use_point: 500 },
    });
  });

  it('201 응답을 Payment로 바꾸고 paidAt은 Date다', async () => {
    request.mockResolvedValue(paymentDto);
    const result = await repo.pay({ reservationId: 'r1', usePoint: 500 });
    expect(result).toEqual({
      id: 'p1',
      reservationId: 'r1',
      amount: 11000,
      status: 'PAID',
      paidAt: new Date('2026-11-10T15:00:00+09:00'),
    });
  });

  it('paid_at이 null이면 paidAt도 null이다', async () => {
    request.mockResolvedValue({ ...paymentDto, paid_at: null });
    const result = await repo.pay({ reservationId: 'r1', usePoint: 0 });
    expect(result.paidAt).toBeNull();
  });

  it('400 INVALID_POINT_AMOUNT ApiError를 그대로 올린다', async () => {
    const err = new ApiError(400, 'INVALID_POINT_AMOUNT', '포인트 초과');
    request.mockRejectedValue(err);
    await expect(repo.pay({ reservationId: 'r1', usePoint: 99999 })).rejects.toBe(err);
  });
});
