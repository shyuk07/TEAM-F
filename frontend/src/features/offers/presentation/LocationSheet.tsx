// open-issues: C1a 주소 입력(주소 → 좌표 변환)은 고객용 API가 없어 만들지 않는다. 현재 위치만 쓴다.
import { useId } from 'react';
import { Overlay } from '@/shared/ui/Overlay';
import type { LocationSheetState } from '../application/useLocationSheet';
import { RADIUS_CHIPS, formatRadiusKm } from '../domain/locationSheet';

export type LocationSheetProps = { sheet: LocationSheetState };

export function LocationSheet({ sheet }: LocationSheetProps) {
  const titleId = useId();
  const labelId = useId();
  return (
    <Overlay onClose={sheet.close}>
      <div className="sheet" role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <div className="t" id={titleId} style={{ fontSize: 17 }}>
          어디서 찾을까요?
        </div>
        <button
          type="button"
          className="btn"
          aria-disabled={!sheet.canUseCurrent ? 'true' : undefined}
          onClick={() => {
            if (sheet.canUseCurrent) sheet.refreshLocation();
          }}
        >
          ◎ 현재 위치 사용
        </button>
        <div className="m" aria-live="polite">
          {sheet.statusLine}
        </div>
        <div className="lbl" id={labelId}>
          반경
        </div>
        <div className="scroll" role="group" aria-labelledby={labelId}>
          {RADIUS_CHIPS.map((km) => {
            const selected = km === sheet.draftRadiusKm;
            return (
              <button
                key={km}
                type="button"
                className={selected ? 'chip on' : 'chip'}
                aria-pressed={selected}
                onClick={() => sheet.selectRadius(km)}
              >
                {formatRadiusKm(km)}
              </button>
            );
          })}
        </div>
        <div className="m">위치를 허용하지 않으면 거리 없이 전체 할인을 보여 줘요.</div>
        <button type="button" className="btn pri" onClick={sheet.apply}>
          적용
        </button>
      </div>
    </Overlay>
  );
}
