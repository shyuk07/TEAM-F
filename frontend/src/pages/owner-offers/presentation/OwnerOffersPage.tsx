import { useState } from 'react';
import { useNavigate } from 'react-router';
import { useOwnerStore } from '@/entities/store';
import {
  matchesFilter,
  OwnerOfferChips,
  OwnerOfferList,
  StockAdjustForm,
  StockAdjustSheet,
  useAdjustStock,
  useOwnerOffers,
  type Offer,
  type StockMode,
} from '@/features/offers';
import { ROUTES } from '@/shared/lib/routes';
import { AppBar, Button } from '@/shared/ui';
import { OwnerAccountButton, OwnerTopNav } from '@/widgets/owner-nav';

export function OwnerOffersPage() {
  const store = useOwnerStore();
  const navigate = useNavigate();

  const storeId = store?.id ?? '';
  const { status, openOffers, closedOffers, counts, filter, setFilter, reload } =
    useOwnerOffers(storeId);

  const [selectedOffer, setSelectedOffer] = useState<Offer | null>(null);
  const {
    submit: submitAdjust,
    status: adjustStatus,
    errorMessage: adjustError,
    reset: resetAdjust,
  } = useAdjustStock();

  const allOffers = filter === 'CLOSED' ? closedOffers : openOffers;
  const filteredOffers = allOffers.filter((o) => matchesFilter(o, filter));

  const handleAdjustSubmit = async (mode: StockMode, amount: number, reason?: string) => {
    if (!selectedOffer) return;
    const res = await submitAdjust(selectedOffer, mode, amount, reason);
    if (res !== null) {
      setSelectedOffer(null);
      resetAdjust();
      await reload();
    }
  };

  const handleAdjustClose = () => {
    setSelectedOffer(null);
    resetAdjust();
  };

  // 모바일 바텀시트는 화면 폭 720px 미만일 때만 오버레이로 띄운다 (PC는 우측 패널)
  const isMobile = typeof window !== 'undefined' ? window.innerWidth < 720 : true;

  return (
    <>
      <AppBar
        logo
        title="할인"
        right={
          <>
            <OwnerTopNav />
            <OwnerAccountButton />
          </>
        }
      />

      <div className="body split r">
        <div className="grid">
          <Button variant="primary" desktopOnly onClick={() => navigate(ROUTES.ownerOfferNew)}>
            + 할인 등록
          </Button>

          <OwnerOfferChips current={filter} counts={counts} onChange={setFilter} />

          <OwnerOfferList
            status={status}
            offers={filteredOffers}
            filter={filter}
            now={new Date()}
            onRetry={reload}
            onEdit={(o) => navigate(ROUTES.ownerOfferEdit(o.id))}
            onAdjust={(o) => setSelectedOffer(o)}
            onDeactivate={(o) => navigate(ROUTES.ownerOfferDeactivate(o.id))}
            onRelist={(o) => navigate(ROUTES.ownerOfferRelist(o.id))}
          />
        </div>

        {selectedOffer && (
          <div
            className="box dk"
            style={{
              alignSelf: 'start',
              flexDirection: 'column',
              background: 'var(--fill)',
            }}
          >
            <StockAdjustForm
              offer={selectedOffer}
              isPending={adjustStatus === 'running'}
              errorMessage={adjustError}
              onSubmit={handleAdjustSubmit}
              onCancel={handleAdjustClose}
            />
          </div>
        )}
      </div>

      <div className="cta">
        <Button variant="primary" onClick={() => navigate(ROUTES.ownerOfferNew)}>
          + 할인 등록
        </Button>
      </div>

      {isMobile && (
        <StockAdjustSheet
          offer={selectedOffer}
          isOpen={selectedOffer !== null}
          isPending={adjustStatus === 'running'}
          errorMessage={adjustError}
          onClose={handleAdjustClose}
          onSubmit={handleAdjustSubmit}
        />
      )}
    </>
  );
}
