import type { HomeView } from '../domain/homeFilter';
import {
  VIEW_BY_OFFER_LABEL,
  VIEW_BY_STORE_LABEL,
  VIEW_GROUP_LABEL,
} from '../domain/offerMessages';

const VIEW_OPTIONS: readonly { view: HomeView; label: string }[] = [
  { view: 'offer', label: VIEW_BY_OFFER_LABEL },
  { view: 'store', label: VIEW_BY_STORE_LABEL },
];

// 「상품별 | 가게별」 보기 전환 칩 2개(와이어프레임 밖 기능, 사용자 승인).
export function ViewToggle({
  value,
  onChange,
}: {
  value: HomeView;
  onChange(view: HomeView): void;
}) {
  return (
    <div className="scroll" role="group" aria-label={VIEW_GROUP_LABEL}>
      {VIEW_OPTIONS.map((o) => {
        const on = o.view === value;
        return (
          <button
            key={o.view}
            type="button"
            className={on ? 'chip on' : 'chip'}
            aria-pressed={on}
            onClick={() => {
              if (!on) onChange(o.view);
            }}
          >
            {o.label}
          </button>
        );
      })}
    </div>
  );
}
