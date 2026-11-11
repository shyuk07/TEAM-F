import { vi } from 'vitest';
import type { OfferCommands } from '@/features/offers';

export class FakeOfferCommands implements OfferCommands {
  register = vi.fn<OfferCommands['register']>();
  relist = vi.fn<OfferCommands['relist']>();
  update = vi.fn<OfferCommands['update']>();
  deactivate = vi.fn<OfferCommands['deactivate']>();
  adjustStock = vi.fn<OfferCommands['adjustStock']>();
}
