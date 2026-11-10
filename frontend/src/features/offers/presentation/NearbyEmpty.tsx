import type { RadiusKm } from '../domain/nearbyQuery';

export function NearbyEmpty(props: { action: RadiusKm | null; onAction(r: RadiusKm): void }) {
  void props;
  return null;
}
