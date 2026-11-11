import { Button } from '@/shared/ui/Button';
import { OWNER_OFFER_MESSAGES } from '../domain/ownerOfferMessages';

export type OfferLoadErrorProps = {
  message?: string;
  onRetry?: () => void;
};

export function OfferLoadError({
  message = OWNER_OFFER_MESSAGES.LOAD_OFFER_FAILED,
  onRetry,
}: OfferLoadErrorProps) {
  return (
    <div className="warn" style={{ textAlign: 'center', padding: 'var(--s4) var(--s2)' }}>
      <p>{message}</p>
      {onRetry && (
        <Button size="sm" onClick={onRetry} style={{ marginTop: 'var(--s2)' }}>
          {OWNER_OFFER_MESSAGES.RETRY}
        </Button>
      )}
    </div>
  );
}
