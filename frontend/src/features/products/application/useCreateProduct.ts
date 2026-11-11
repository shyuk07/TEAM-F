import { useCallback } from 'react';
import { useDep } from '@/shared/lib/di';
import type { Product } from '@/entities/product';
import type { ProductFormValue } from '../domain/productForm';
import { productErrorMessage } from '../domain/productMessages';
import { createProduct } from './createProduct';
import { ProductCommandsToken } from './tokens';
import { useProductRun } from './useProductRun';

const PHOTO_ERROR_CODES = ['IMAGE_TOO_LARGE', 'UNSUPPORTED_IMAGE_TYPE'];

export function useCreateProduct(): {
  submit(storeId: string, value: ProductFormValue, photo: Blob | null): Promise<Product | null>;
  status: 'idle' | 'submitting' | 'error';
  errorMessage: string | null;
  photoError: boolean;
  reset(): void;
} {
  const commands = useDep(ProductCommandsToken);
  const { run, status, errorMessage, errorCode, reset } = useProductRun();
  const submit = useCallback(
    (storeId: string, value: ProductFormValue, photo: Blob | null) =>
      run((signal) => createProduct({ commands }, { storeId, value, photo }, signal), {
        message: (info) => productErrorMessage(info, 'create'),
      }),
    [commands, run],
  );
  return {
    submit,
    status: status === 'running' ? 'submitting' : status,
    errorMessage,
    photoError: errorCode !== null && PHOTO_ERROR_CODES.includes(errorCode),
    reset,
  };
}
