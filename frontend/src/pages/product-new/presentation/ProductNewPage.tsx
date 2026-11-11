import { Link, useNavigate } from 'react-router';
import { useOwnerStore } from '@/entities/store';
import { ProductCreateForm } from '@/features/products';
import { ROUTES } from '@/shared/lib/routes';
import { AppBar } from '@/shared/ui';
import { OwnerAccountButton, OwnerTopNav } from '@/widgets/owner-nav';

// O6 상품 등록(products.md §5.2). 성공 뒤 이동은 replace 없이 한다.
export function ProductNewPage() {
  const store = useOwnerStore();
  const navigate = useNavigate();

  if (store === null) return null;

  return (
    <>
      <AppBar
        title="상품 등록"
        left={
          <Link to={ROUTES.ownerStore} aria-label="뒤로">
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
      <ProductCreateForm
        storeId={store.id}
        onCreated={(product, intent) =>
          navigate(intent === 'offer' ? ROUTES.ownerOfferNewFor(product.id) : ROUTES.ownerStore)
        }
      />
    </>
  );
}
