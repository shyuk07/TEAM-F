import { bind, type Binding } from '@/shared/lib/di';
import { ProductRepositoryToken } from '@/entities/product';
import { ProductCommandsToken } from './application/tokens';
import { HttpProductCommands } from './infrastructure/httpProductCommands';
import { HttpProductRepository } from './infrastructure/httpProductRepository';

export function wireProducts(): Binding[] {
  return [
    bind(ProductRepositoryToken, new HttpProductRepository()), // 소유한 entities 포트
    bind(ProductCommandsToken, new HttpProductCommands()), // 이 영역의 포트
  ];
}
