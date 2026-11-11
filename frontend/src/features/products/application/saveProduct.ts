import type { Product } from '@/entities/product';
import { hasChanges, type ProductChanges } from '../domain/productChanges';
import type { ProductCommands } from '../domain/productCommands';

export async function saveProduct(
  deps: { commands: ProductCommands },
  input: { original: Product; changes: ProductChanges },
  signal?: AbortSignal,
): Promise<Product> {
  if (!hasChanges(input.changes)) return input.original;
  return deps.commands.update(input.original.id, input.changes, signal);
}
