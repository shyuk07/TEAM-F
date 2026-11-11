import type { SalesStart } from '../domain/offerDraft';

export type OfferScheduleFieldsProps = {
  salesStart: SalesStart;
  salesEnd: Date;
  pickupStart: Date;
  pickupEnd: Date;
  now: Date;
  disabled?: boolean;
  onSalesStartChange?: (date: Date) => void;
  onSalesEndChange?: (date: Date) => void;
  onPickupStartChange?: (date: Date) => void;
  onPickupEndChange?: (date: Date) => void;
};

function toLocalDatetimeString(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0');
  const year = d.getFullYear();
  const month = pad(d.getMonth() + 1);
  const day = pad(d.getDate());
  const hours = pad(d.getHours());
  const minutes = pad(d.getMinutes());
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

export function OfferScheduleFields({
  salesStart,
  salesEnd,
  pickupStart,
  pickupEnd,
  now,
  disabled,
  onSalesStartChange,
  onSalesEndChange,
  onPickupStartChange,
  onPickupEndChange,
}: OfferScheduleFieldsProps) {
  const effectiveStart = salesStart === 'now' ? now : salesStart;

  return (
    <div style={{ display: 'grid', gap: 'var(--s2)' }}>
      <div className="row">
        <div style={{ flex: 1 }}>
          <div className="lbl">판매 시작</div>
          <input
            type="datetime-local"
            className="in"
            value={toLocalDatetimeString(effectiveStart)}
            disabled={disabled}
            onChange={(e) => {
              const val = new Date(e.target.value);
              if (!isNaN(val.getTime())) {
                onSalesStartChange?.(val);
              }
            }}
          />
        </div>
        <div style={{ flex: 1 }}>
          <div className="lbl">판매 마감 *</div>
          <input
            type="datetime-local"
            className="in"
            value={toLocalDatetimeString(salesEnd)}
            disabled={disabled}
            onChange={(e) => {
              const val = new Date(e.target.value);
              if (!isNaN(val.getTime())) {
                onSalesEndChange?.(val);
              }
            }}
          />
        </div>
      </div>

      <div className="row">
        <div style={{ flex: 1 }}>
          <div className="lbl">픽업 시작 *</div>
          <input
            type="datetime-local"
            className="in"
            value={toLocalDatetimeString(pickupStart)}
            disabled={disabled}
            onChange={(e) => {
              const val = new Date(e.target.value);
              if (!isNaN(val.getTime())) {
                onPickupStartChange?.(val);
              }
            }}
          />
        </div>
        <div style={{ flex: 1 }}>
          <div className="lbl">픽업 종료 *</div>
          <input
            type="datetime-local"
            className="in"
            value={toLocalDatetimeString(pickupEnd)}
            disabled={disabled}
            onChange={(e) => {
              const val = new Date(e.target.value);
              if (!isNaN(val.getTime())) {
                onPickupEndChange?.(val);
              }
            }}
          />
        </div>
      </div>
    </div>
  );
}
