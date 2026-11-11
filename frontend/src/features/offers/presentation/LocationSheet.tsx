import { useId, useState } from 'react';
import { locationStatusText } from '../domain/homeFilter';
import { RADIUS_OPTIONS, type RadiusKm } from '../domain/nearbyQuery';
import {
  LOCATION_DENIED_HINT,
  LOCATION_SHEET_TITLE,
  USE_CURRENT_LOCATION_LABEL,
} from '../domain/offerMessages';

// C1a 위치·반경 시트(wireframe.html:331~339, customer-home.md §3.5, D-15).
// 반경은 「적용」 때만 반영하고, Escape·바깥 누름은 Overlay가 적용 없이 닫는다(C-14).
// open-issues: C1a 주소를 입력해 위치 바꾸기 없음 (현재 위치만)
export function LocationSheet({
  hasLocation,
  locating,
  radiusKm,
  onUseCurrentLocation,
  onApply,
}: {
  hasLocation: boolean;
  locating: boolean;
  radiusKm: RadiusKm;
  onUseCurrentLocation(): void;
  onApply(radiusKm: RadiusKm): void;
}) {
  const titleId = useId();
  // 시트 안 선택값. 처음은 지금 반경.
  const [selected, setSelected] = useState<RadiusKm>(radiusKm);

  return (
    <div className="sheet" role="dialog" aria-modal="true" aria-labelledby={titleId}>
      <div className="t" id={titleId} style={{ fontSize: 17 }}>
        {LOCATION_SHEET_TITLE}
      </div>
      <button
        type="button"
        className="btn"
        aria-disabled={locating ? 'true' : undefined}
        onClick={() => {
          if (!locating) onUseCurrentLocation();
        }}
      >
        {locating ? '처리 중…' : USE_CURRENT_LOCATION_LABEL}
      </button>
      <div className="m">{locationStatusText(hasLocation)}</div>
      <div className="lbl">반경</div>
      <div className="scroll">
        {RADIUS_OPTIONS.map((r) => (
          <button
            key={r}
            type="button"
            className={r === selected ? 'chip on' : 'chip'}
            aria-pressed={r === selected}
            onClick={() => setSelected(r)}
          >
            {`${r}km`}
          </button>
        ))}
      </div>
      <div className="m">{LOCATION_DENIED_HINT}</div>
      <button type="button" className="btn pri" onClick={() => onApply(selected)}>
        적용
      </button>
    </div>
  );
}
