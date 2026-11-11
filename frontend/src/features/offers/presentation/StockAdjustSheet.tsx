import { Overlay } from '@/shared/ui/Overlay';
import type { Offer } from '../domain/offer';
import type { StockMode } from '../domain/stockAdjustment';
import { StockAdjustForm } from './StockAdjustForm';

export type StockAdjustSheetProps = {
  offer: Offer | null;
  isOpen: boolean;
  isPending?: boolean;
  errorMessage?: string | null;
  onClose: () => void;
  onSubmit: (mode: StockMode, amount: number, reason?: string) => Promise<void>;
};

export function StockAdjustSheet({
  offer,
  isOpen,
  isPending,
  errorMessage,
  onClose,
  onSubmit,
}: StockAdjustSheetProps) {
  if (!isOpen || !offer) return null;

  return (
    <Overlay onClose={onClose} dismissible={!isPending}>
      <div
        className="sheet"
        role="dialog"
        aria-modal="true"
        aria-label={`재고 조정 - ${offer.productName}`}
      >
        <StockAdjustForm
          offer={offer}
          isPending={isPending}
          errorMessage={errorMessage}
          onSubmit={onSubmit}
          onCancel={onClose}
        />
      </div>
    </Overlay>
  );
}
