import { useCallback } from 'react';
import { useDep } from '@/shared/lib/di';
import type { Product } from '@/entities/product';
import { productErrorMessage } from '../domain/productMessages';
import { ProductCommandsToken } from './tokens';
import { toggleProduct } from './toggleProduct';
import { useProductRun } from './useProductRun';

// open-issues: O11 숨기기 확인 단계 없음, 진행 중 할인으로 서버가 거절하면 안내만 보인다 (사용자 결정 products.md D-3)
export function useToggleProduct(): {
  toggle(product: Product): Promise<Product | null>;
  status: 'idle' | 'pending' | 'error';
  errorMessage: string | null;
} {
  const commands = useDep(ProductCommandsToken);
  const { run, status, errorMessage } = useProductRun();
  const toggle = useCallback(
    (product: Product) =>
      run((signal) => toggleProduct({ commands }, product, signal), {
        message: (info) => productErrorMessage(info, 'toggle'),
      }),
    [commands, run],
  );
  return { toggle, status: status === 'running' ? 'pending' : status, errorMessage };
}
