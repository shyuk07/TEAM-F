import { Container } from '@/shared/lib/di';
import { wireAuth } from '@/features/auth/wiring';
import { wireOffers } from '@/features/offers/wiring';

export function createContainer(): Container {
  return new Container([...wireAuth(), ...wireOffers()]);
}
