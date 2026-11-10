import { SORT_CHIPS, isSortSelectable, type OfferSortKey } from '../domain/search';
// TODO: 비활성 칩 모양이 임시다(opacity 0.4).
//   왜: Chip 비활성 상태 정본이 없다 (docs/design/frontend/offers.md C-5)
//   언제: 결정 후 (디자인 시스템: Chip 비활성 상태)
import styles from './SortChips.module.css';

export type SortChipsProps = {
  sort: OfferSortKey;
  hasLocation: boolean;
  onSelect: (key: OfferSortKey) => void;
};

export function SortChips({ sort, hasLocation, onSelect }: SortChipsProps) {
  return (
    <div className="scroll">
      {SORT_CHIPS.map((chip) => {
        const selectable = isSortSelectable(chip.key, hasLocation);
        const classes = ['chip'];
        if (chip.key === sort) classes.push('on');
        if (!selectable) classes.push(styles.disabled);
        return (
          <button
            key={chip.key}
            type="button"
            className={classes.join(' ')}
            aria-pressed={chip.key === sort}
            disabled={!selectable}
            aria-disabled={selectable ? undefined : true}
            onClick={() => {
              if (selectable) onSelect(chip.key);
            }}
          >
            {chip.label}
          </button>
        );
      })}
    </div>
  );
}
