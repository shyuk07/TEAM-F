import { apiPost } from '@/shared/api/client';
import type { Payment } from '../domain/payment';
import type { PaymentRepository } from '../domain/ports';

type PaymentDto = {
  id: string;
  reservation_id: string;
  amount: number;
  status: string;
  paid_at: string | null;
};

export class HttpPaymentRepository implements PaymentRepository {
  async pay(
    input: { reservationId: string; usePoint: number },
    signal?: AbortSignal,
  ): Promise<Payment> {
    const dto = await apiPost<PaymentDto>(
      '/v1/payments',
      { reservation_id: input.reservationId, use_point: input.usePoint },
      signal,
    );
    return {
      id: dto.id,
      reservationId: dto.reservation_id,
      amount: dto.amount,
      status: dto.status,
      paidAt: dto.paid_at === null ? null : new Date(dto.paid_at),
    };
  }
}
