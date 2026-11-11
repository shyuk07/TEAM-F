import { createToken } from '@/shared/lib/di';
import type { ProductCommands } from '../domain/productCommands';

export const ProductCommandsToken = createToken<ProductCommands>('ProductCommands');
