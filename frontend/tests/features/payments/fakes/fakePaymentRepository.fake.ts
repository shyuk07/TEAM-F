import { vi } from 'vitest';
import type { PaymentRepository } from '@/features/payments/domain/ports';

export class FakePaymentRepository implements PaymentRepository {
  pay = vi.fn<PaymentRepository['pay']>((input) =>
    Promise.resolve({
      id: 'p1',
      reservationId: input.reservationId,
      amount: 11500 - input.usePoint,
      status: 'PAID',
      paidAt: new Date('2026-11-10T15:00:00+09:00'),
    }),
  );
}
