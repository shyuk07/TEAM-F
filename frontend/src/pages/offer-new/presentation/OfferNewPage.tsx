import { useMemo } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router';
import { useOwnerStore } from '@/entities/store';
import {
  defaultDraft,
  OfferCreateForm,
  OfferLoadError,
  useCreateOffer,
  useOwnerOffer,
  useSellableProducts,
  type CreateOfferMode,
  type OfferDraft,
} from '@/features/offers';
import { ROUTES } from '@/shared/lib/routes';
import { AppBar, Button } from '@/shared/ui';
import { OwnerAccountButton, OwnerTopNav } from '@/widgets/owner-nav';

export function OfferNewPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const store = useOwnerStore();

  const productIdParam = params.get('productId') ?? '';
  const relistFromParam = params.get('relistFrom') ?? '';

  const { products, status: productsStatus } = useSellableProducts(store?.id ?? '');
  const {
    offer: sourceOffer,
    status: sourceStatus,
    reload: reloadSource,
  } = useOwnerOffer(relistFromParam);

  const { submit, status: submitStatus, errorMessage } = useCreateOffer();

  const isRelist = Boolean(relistFromParam);
  const now = useMemo(() => new Date(), []);

  const initialDraft: OfferDraft = useMemo(() => {
    if (sourceOffer) {
      return defaultDraft(now, {
        productId: sourceOffer.productId,
        salePrice: sourceOffer.salePrice,
        initialStock: sourceOffer.initialStock,
      });
    }
    return defaultDraft(now, {
      productId: productIdParam,
    });
  }, [now, productIdParam, sourceOffer]);

  if (isRelist && sourceStatus === 'loading') {
    return (
      <>
        <AppBar
          title="할인 등록"
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

  if (isRelist && sourceStatus === 'error') {
    return (
      <>
        <AppBar
          title="할인 등록"
          left={
            <Link to={ROUTES.ownerOffers} aria-label="뒤로">
              ←
            </Link>
          }
        />
        <div className="body">
          <OfferLoadError onRetry={reloadSource} />
        </div>
      </>
    );
  }

  const handleSubmit = async (draft: OfferDraft) => {
    let mode: CreateOfferMode = 'new';
    if (isRelist && sourceOffer) {
      // D-7, C-2: 서버 /relist는 is_active=false인 할인을 400 거절하므로 register(새 할인)로 우회
      mode = sourceOffer.isActive ? 'relist' : 'refill';
    }

    const res = await submit({
      mode,
      productId: draft.productId,
      sourceOfferId: relistFromParam || undefined,
      draft,
      now: new Date(),
    });

    if (res !== null) {
      navigate(ROUTES.ownerOffers);
    }
  };

  const buttonText = isRelist ? '다시 올리기' : '할인 등록';

  return (
    <>
      <AppBar
        title={buttonText}
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
        {productsStatus === 'loading' ? (
          <div className="sk" style={{ height: 200 }} />
        ) : (
          <OfferCreateForm
            formId="offer-create-form"
            products={products}
            initialDraft={initialDraft}
            now={now}
            isPending={submitStatus === 'running'}
            errorMessage={errorMessage}
            submitButtonText={buttonText}
            onSubmit={handleSubmit}
          />
        )}
      </div>

      <div className="cta">
        <Button
          form="offer-create-form"
          type="submit"
          variant="primary"
          pending={submitStatus === 'running'}
          style={{ width: '100%' }}
        >
          {buttonText}
        </Button>
      </div>
    </>
  );
}
