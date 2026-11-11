import { Box } from '@/shared/ui/Box';
import { Button } from '@/shared/ui/Button';
import { StatusTag } from '@/shared/ui/StatusTag';
import type { Offer } from '../domain/offer';
import { ownerRowActions, ownerRowSummary, ownerStatusTag } from '../domain/ownerOffer';

export type OwnerOfferRowProps = {
  offer: Offer;
  now: Date;
  onEdit?: (offer: Offer) => void;
  onAdjust?: (offer: Offer) => void;
  onDeactivate?: (offer: Offer) => void;
  onRelist?: (offer: Offer) => void;
};

export function OwnerOfferRow({
  offer,
  now,
  onEdit,
  onAdjust,
  onDeactivate,
  onRelist,
}: OwnerOfferRowProps) {
  const tag = ownerStatusTag(offer);
  const actions = ownerRowActions(offer, now);
  const { title, meta, countdown } = ownerRowSummary(offer, now);

  return (
    <Box>
      <div className="row">
        {tag.tone ? (
          <StatusTag tone={tag.tone}>{tag.label}</StatusTag>
        ) : (
          <span className="tag">{tag.label}</span>
        )}
        {countdown && (
          <>
            <span className="sp" />
            <span className="cd">{countdown}</span>
          </>
        )}
      </div>

      <div className="t">{title}</div>
      <div className="m">{meta}</div>

      {actions.length > 0 && (
        <div className="row" style={{ marginTop: 'var(--s1)' }}>
          {actions.includes('edit') && (
            <Button size="sm" onClick={() => onEdit?.(offer)}>
              수정
            </Button>
          )}
          {actions.includes('adjust') && (
            <Button size="sm" onClick={() => onAdjust?.(offer)}>
              재고 조정
            </Button>
          )}
          {actions.includes('relist') && (
            <Button size="sm" onClick={() => onRelist?.(offer)}>
              다시 올리기
            </Button>
          )}
          {actions.includes('deactivate') && (
            <>
              <span className="sp" />
              <button
                type="button"
                className="link"
                style={{
                  background: 'none',
                  border: 'none',
                  padding: 0,
                  font: 'inherit',
                  cursor: 'pointer',
                  color: 'var(--mute)',
                }}
                onClick={() => onDeactivate?.(offer)}
              >
                판매 중단
              </button>
            </>
          )}
        </div>
      )}
    </Box>
  );
}
