import { createToken } from '@/shared/lib/di';
import type { OfferCommands } from '../domain/offerCommands';
import type { OfferRepository } from '../domain/offerRepository';
import type { LocationProvider, MapRenderer } from './ports';

export const OfferRepositoryToken = createToken<OfferRepository>('OfferRepository');

export const OfferCommandsToken = createToken<OfferCommands>('OfferCommands');

export const LocationProviderToken = createToken<LocationProvider>('LocationProvider');

export const MapRendererToken = createToken<MapRenderer>('MapRenderer');
