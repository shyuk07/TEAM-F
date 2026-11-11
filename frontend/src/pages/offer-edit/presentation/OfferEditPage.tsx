import { Link, useNavigate, useParams } from 'react-router';
import {
  diffOfferChanges,
  OfferEditForm,
  OfferLoadError,
  useOwnerOffer,
  useSaveOffer,
  type OfferEditValues,
} from '@/features/offers';
import { ROUTES } from '@/shared/lib/routes';
import { AppBar, Button } from '@/shared/ui';
import { OwnerAccountButton, OwnerTopNav } from '@/widgets/owner-nav';

export function OfferEditPage() {
  const { offerId = '' } = useParams<{ offerId: string }>();
  const navigate = useNavigate();

  const { offer, status, failure, reload } = useOwnerOffer(offerId);
  const { submit, status: saveStatus, errorMessage, isLocked } = useSaveOffer();

  if (status === 'loading') {
    return (
      <>
        <AppBar
          title="할인 수정"
          left={
            <Link to={ROUTES.ownerOffers} aria-label="뒤로">
              ←
            </Link>
          }
        />
        <div className="body">
          <div className="sk" style={{ height: 250 }} />
        </div>
      </>
    );
  }

  if (status === 'error' || !offer) {
    return (
      <>
        <AppBar
          title="할인 수정"
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

  const handleSubmit = async (values: OfferEditValues) => {
    const changes = diffOfferChanges(offer, values);
    const res = await submit(offer.id, changes);
    if (res !== null) {
      navigate(ROUTES.ownerOffers);
    }
  };

  return (
    <>
      <AppBar
        title="할인 수정"
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
        <OfferEditForm
          formId="offer-edit-form"
          offer={offer}
          now={new Date()}
          isPending={saveStatus === 'running'}
          isLocked={isLocked}
          errorMessage={errorMessage}
          onDeactivateClick={() => navigate(ROUTES.ownerOfferDeactivate(offer.id))}
          onSubmit={handleSubmit}
        />
      </div>

      <div className="cta">
        <Button
          form="offer-edit-form"
          type="submit"
          variant="primary"
          pending={saveStatus === 'running'}
          disabled={isLocked}
          style={{ width: '100%' }}
        >
          저장
        </Button>
      </div>
    </>
  );
}
