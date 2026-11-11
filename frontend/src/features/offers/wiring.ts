import { bind, type Binding } from '@/shared/lib/di';
import {
  LocationProviderToken,
  MapRendererToken,
  OfferCommandsToken,
  OfferRepositoryToken,
} from './application/tokens';
import { BrowserLocationProvider } from './infrastructure/browserLocationProvider';
import { HttpOfferCommands } from './infrastructure/httpOfferCommands';
import { HttpOfferRepository } from './infrastructure/httpOfferRepository';
import { KakaoMapRenderer } from './infrastructure/kakaoMapRenderer';

export function wireOffers(): Binding[] {
  return [
    bind(OfferRepositoryToken, new HttpOfferRepository()),
    bind(OfferCommandsToken, new HttpOfferCommands()),
    bind(LocationProviderToken, new BrowserLocationProvider()),
    bind(MapRendererToken, new KakaoMapRenderer()),
  ];
}
