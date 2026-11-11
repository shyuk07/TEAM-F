import { Button } from '@/shared/ui/Button';
import { EmptyState } from '@/shared/ui/EmptyState';
import { Skeleton } from '@/shared/ui/Skeleton';
import type { Offer } from '../domain/offer';
import type { OwnerFilter } from '../domain/ownerOffer';
import { OWNER_OFFER_MESSAGES } from '../domain/ownerOfferMessages';
import { OwnerOfferRow } from './OwnerOfferRow';

export type OwnerOfferListProps = {
  status: 'loading' | 'success' | 'error';
  offers: Offer[];
  filter: OwnerFilter;
  now: Date;
  onRetry?: () => void;
  onEdit?: (offer: Offer) => void;
  onAdjust?: (offer: Offer) => void;
  onDeactivate?: (offer: Offer) => void;
  onRelist?: (offer: Offer) => void;
};

export function OwnerOfferList({
  status,
  offers,
  filter,
  now,
  onRetry,
  onEdit,
  onAdjust,
  onDeactivate,
  onRelist,
}: OwnerOfferListProps) {
  if (status === 'loading') {
    return (
      <div style={{ display: 'grid', gap: 'var(--s2)' }}>
        <Skeleton />
        <Skeleton />
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="warn" style={{ textAlign: 'center', padding: 'var(--s4) var(--s2)' }}>
        <p>{OWNER_OFFER_MESSAGES.LOAD_FAILED}</p>
        {onRetry && (
          <Button size="sm" onClick={onRetry} style={{ marginTop: 'var(--s2)' }}>
            {OWNER_OFFER_MESSAGES.RETRY}
          </Button>
        )}
      </div>
    );
  }

  if (offers.length === 0) {
    let emptyMessage: string = OWNER_OFFER_MESSAGES.EMPTY_ON_SALE;
    if (filter === 'SCHEDULED') emptyMessage = OWNER_OFFER_MESSAGES.EMPTY_SCHEDULED;
    else if (filter === 'SOLD_OUT') emptyMessage = OWNER_OFFER_MESSAGES.EMPTY_SOLD_OUT;
    else if (filter === 'CLOSED') emptyMessage = OWNER_OFFER_MESSAGES.EMPTY_CLOSED;

    return <EmptyState title={emptyMessage} />;
  }

  return (
    <div style={{ display: 'grid', gap: 'var(--s2)' }}>
      {offers.map((offer) => (
        <OwnerOfferRow
          key={offer.id}
          offer={offer}
          now={now}
          onEdit={onEdit}
          onAdjust={onAdjust}
          onDeactivate={onDeactivate}
          onRelist={onRelist}
        />
      ))}
    </div>
  );
}
