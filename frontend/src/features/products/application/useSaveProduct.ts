import { useCallback } from 'react';
import { useDep } from '@/shared/lib/di';
import type { Product } from '@/entities/product';
import type { ProductChanges } from '../domain/productChanges';
import { productErrorMessage } from '../domain/productMessages';
import { saveProduct } from './saveProduct';
import { ProductCommandsToken } from './tokens';
import { useProductRun } from './useProductRun';

export function useSaveProduct(): {
  submit(original: Product, changes: ProductChanges): Promise<Product | null>;
  status: 'idle' | 'submitting' | 'error';
  errorMessage: string | null;
  reset(): void;
} {
  const commands = useDep(ProductCommandsToken);
  const { run, status, errorMessage, reset } = useProductRun();
  const submit = useCallback(
    (original: Product, changes: ProductChanges) =>
      run((signal) => saveProduct({ commands }, { original, changes }, signal), {
        message: (info) => productErrorMessage(info, 'save'),
      }),
    [commands, run],
  );
  return {
    submit,
    status: status === 'running' ? 'submitting' : status,
    errorMessage,
    reset,
  };
}
