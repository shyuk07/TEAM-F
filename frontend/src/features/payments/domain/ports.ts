import type { Payment } from './payment';

export interface PaymentRepository {
  pay(input: { reservationId: string; usePoint: number }, signal?: AbortSignal): Promise<Payment>;
}
