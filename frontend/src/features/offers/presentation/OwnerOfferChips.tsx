import { Chip } from '@/shared/ui/Chip';
import { OWNER_FILTERS, type OwnerFilter } from '../domain/ownerOffer';

export type OwnerOfferChipsProps = {
  current: OwnerFilter;
  counts: { onSale: number; scheduled: number; soldOut: number };
  onChange: (filter: OwnerFilter) => void;
};

export function OwnerOfferChips({ current, counts, onChange }: OwnerOfferChipsProps) {
  const getLabel = (key: OwnerFilter, baseLabel: string) => {
    if (key === 'ON_SALE') return `${baseLabel} ${counts.onSale}`;
    if (key === 'SCHEDULED') return `${baseLabel} ${counts.scheduled}`;
    return baseLabel;
  };

  return (
    <div className="scroll" role="toolbar" aria-label="할인 상태 필터">
      {OWNER_FILTERS.map((f) => (
        <Chip key={f.key} selected={current === f.key} onClick={() => onChange(f.key)}>
          {getLabel(f.key, f.label)}
        </Chip>
      ))}
    </div>
  );
}
