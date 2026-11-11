import type { Product } from '@/entities/product';
import { readErrorInfo } from '@/shared/lib/errorInfo';
import type { ProductCommands } from '../domain/productCommands';
import { productWhenAlready } from '../domain/productToggle';

// 이미 원하는 상태라는 서버 응답(PRODUCT_ALREADY_*)은 성공으로 보고 그 상태의 Product를 돌려준다(D-33).
export async function toggleProduct(
  deps: { commands: ProductCommands },
  product: Product,
  signal?: AbortSignal,
): Promise<Product> {
  try {
    return product.isActive
      ? await deps.commands.deactivate(product.id, signal)
      : await deps.commands.activate(product.id, signal);
  } catch (e) {
    const already = productWhenAlready(product, readErrorInfo(e).errorCode);
    if (already === null) throw e;
    return already;
  }
}
