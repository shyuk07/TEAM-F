import type { Product } from '@/entities/product';
import type { ProductCommands } from '../domain/productCommands';
import type { ProductFormValue } from '../domain/productForm';

// 사진과 상품은 한 요청으로 보낸다(서버가 원자 처리). 가공 없음.
export function createProduct(
  deps: { commands: ProductCommands },
  input: { storeId: string; value: ProductFormValue; photo: Blob | null },
  signal?: AbortSignal,
): Promise<Product> {
  const { name, originalPrice, category, description } = input.value;
  return deps.commands.create(
    input.storeId,
    { name, originalPrice, category, description },
    input.photo,
    signal,
  );
}
