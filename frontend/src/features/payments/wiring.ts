import { bind, type Binding } from '@/shared/lib/di';
import { PaymentRepositoryToken } from './application/tokens';
import { HttpPaymentRepository } from './infrastructure/httpPaymentRepository';

export function wirePayments(): Binding[] {
  return [bind(PaymentRepositoryToken, new HttpPaymentRepository())];
}
