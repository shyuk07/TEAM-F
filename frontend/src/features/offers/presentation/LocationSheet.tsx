import type { RadiusKm } from '../domain/nearbyQuery';

export function LocationSheet(props: {
  hasLocation: boolean;
  locating: boolean;
  radiusKm: RadiusKm;
  onUseCurrentLocation(): void;
  onApply(radiusKm: RadiusKm): void;
  onClose(): void;
}) {
  void props;
  return null;
}
