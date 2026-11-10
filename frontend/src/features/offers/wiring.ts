import { bind, type Binding } from '@/shared/lib/di';
import { LocationProviderToken, OfferRepositoryToken } from './application/tokens';
import { BrowserLocationProvider } from './infrastructure/browserLocationProvider';
import { HttpOfferRepository } from './infrastructure/httpOfferRepository';

export function wireOffers(): Binding[] {
  return [
    bind(OfferRepositoryToken, new HttpOfferRepository()),
    bind(LocationProviderToken, new BrowserLocationProvider()),
  ];
}
