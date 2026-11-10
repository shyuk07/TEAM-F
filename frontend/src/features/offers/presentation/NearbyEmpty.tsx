import type { RadiusKm } from '../domain/nearbyQuery';
import { NEARBY_EMPTY_HINT, NEARBY_EMPTY_TITLE, widenRadiusLabel } from '../domain/offerMessages';

// 빈 상태(wireframe.html:546, E1). 넓힐 반경이 없으면(위치 없음·10km) 버튼 없이 문구만(customer-home.md C-8).
export function NearbyEmpty({
  action,
  onAction,
}: {
  action: RadiusKm | null;
  onAction(r: RadiusKm): void;
}) {
  return (
    <div className="box empty">
      <div className="ic" />
      <b>{NEARBY_EMPTY_TITLE}</b>
      <span className="m">{NEARBY_EMPTY_HINT}</span>
      {action !== null ? (
        <button type="button" className="btn sm" onClick={() => onAction(action)}>
          {widenRadiusLabel(action)}
        </button>
      ) : null}
    </div>
  );
}
