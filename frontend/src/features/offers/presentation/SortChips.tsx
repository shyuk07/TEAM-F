import { SORT_OPTIONS, effectiveSort, isSortAvailable } from '../domain/homeFilter';
import type { OfferSort } from '../domain/nearbyQuery';
import { SORT_GROUP_LABEL } from '../domain/offerMessages';

// 정렬 칩(wireframe.html:306). 선택 표시는 실제로 요청하는 정렬 기준, 쓸 수 없는 칩은 눌러도 무시(D-11).
export function SortChips({
  value,
  hasLocation,
  onChange,
}: {
  value: OfferSort;
  hasLocation: boolean;
  onChange(sort: OfferSort): void;
}) {
  const selected = effectiveSort(value, hasLocation);
  return (
    <div className="scroll" role="group" aria-label={SORT_GROUP_LABEL}>
      {SORT_OPTIONS.map((o) => {
        const on = o.sort === selected;
        const available = isSortAvailable(o.sort, hasLocation);
        return (
          <button
            key={o.sort}
            type="button"
            className={on ? 'chip on' : 'chip'}
            aria-pressed={on}
            aria-disabled={available ? undefined : 'true'}
            onClick={() => {
              if (available && !on) onChange(o.sort);
            }}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
