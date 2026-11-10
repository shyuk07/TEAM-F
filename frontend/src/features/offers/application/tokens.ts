import { createToken } from '@/shared/lib/di';
import type { OfferRepository } from '../domain/offerRepository';
import type { LocationProvider } from './ports';

export const OfferRepositoryToken = createToken<OfferRepository>('OfferRepository');
export const LocationProviderToken = createToken<LocationProvider>('LocationProvider');
