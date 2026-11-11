import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router';
import {
  OfferDeactivateForm,
  OfferLoadError,
  useDeactivateOffer,
  useOwnerOffer,
} from '@/features/offers';
import { ROUTES } from '@/shared/lib/routes';
import { AppBar, Button } from '@/shared/ui';
import { OwnerAccountButton, OwnerTopNav } from '@/widgets/owner-nav';

export function OfferDeactivatePage() {
  const { offerId = '' } = useParams<{ offerId: string }>();
  const navigate = useNavigate();

  const { offer, status, failure, reload } = useOwnerOffer(offerId);
  const { submit, status: submitStatus, errorMessage } = useDeactivateOffer();
  const [isFormValid, setIsFormValid] = useState(false);

  if (status === 'loading') {
    return (
      <>
        <AppBar
          title="판매 중단"
          left={
            <Link to={ROUTES.ownerOffers} aria-label="뒤로">
              ←
            </Link>
          }
        />
        <div className="body">
          <div className="sk" style={{ height: 200 }} />
        </div>
      </>
    );
  }

  if (status === 'error' || !offer) {
    return (
      <>
        <AppBar
          title="판매 중단"
          left={
            <Link to={ROUTES.ownerOffers} aria-label="뒤로">
              ←
            </Link>
          }
        />
        <div className="body">
          <OfferLoadError message={failure?.message} onRetry={reload} />
        </div>
      </>
    );
  }

  const handleCancel = () => {
    navigate(ROUTES.ownerOffers);
  };

  const handleSubmit = async (reason: string, cancelReservations: boolean) => {
    const res = await submit(offer.id, { reason, cancelReservations });
    if (res !== null) {
      navigate(ROUTES.ownerOffers);
    }
  };

  return (
    <>
      <AppBar
        title="판매 중단"
        left={
          <Link to={ROUTES.ownerOffers} aria-label="뒤로">
            ←
          </Link>
        }
        right={
          <>
            <OwnerTopNav />
            <OwnerAccountButton />
          </>
        }
      />
      <div className="body">
        <OfferDeactivateForm
          formId="offer-deactivate-form"
          offer={offer}
          isPending={submitStatus === 'running'}
          errorMessage={errorMessage}
          onValidityChange={setIsFormValid}
          onCancel={handleCancel}
          onSubmit={handleSubmit}
        />
      </div>

      <div className="cta" style={{ gap: 'var(--s2)' }}>
        <Button onClick={handleCancel} disabled={submitStatus === 'running'}>
          취소
        </Button>
        <Button
          form="offer-deactivate-form"
          type="submit"
          variant="dark"
          pending={submitStatus === 'running'}
          disabled={!isFormValid}
        >
          판매 중단
        </Button>
      </div>
    </>
  );
}
