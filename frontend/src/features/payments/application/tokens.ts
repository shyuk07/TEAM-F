import { createToken } from '@/shared/lib/di';
import type { PaymentRepository } from '../domain/ports';

export const PaymentRepositoryToken = createToken<PaymentRepository>('PaymentRepository');
