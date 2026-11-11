import { Link, useNavigate, useParams } from 'react-router';
import { ProductEditForm, ProductLoadError, useProduct } from '@/features/products';
import { ROUTES } from '@/shared/lib/routes';
import { AppBar, Skeleton } from '@/shared/ui';
import { OwnerAccountButton, OwnerTopNav } from '@/widgets/owner-nav';

// O11 상품 수정·숨기기(products.md §5.3).
export function ProductEditPage() {
  const { productId = '' } = useParams();
  const product = useProduct(productId);
  const navigate = useNavigate();

  const back = (
    <Link to={ROUTES.ownerStore} aria-label="뒤로">
      ←
    </Link>
  );

  if (product.status === 'loading') {
    return (
      <>
        <AppBar title="상품 수정" left={back} />
        <div className="body" aria-busy="true">
          <Skeleton />
        </div>
      </>
    );
  }

  if (product.status === 'error') {
    return (
      <>
        <AppBar title="상품 수정" left={back} />
        <div className="body">
          {product.failure !== null ? (
            <ProductLoadError failure={product.failure} onRetry={product.reload} />
          ) : null}
        </div>
      </>
    );
  }

  return (
    <>
      <AppBar
        title="상품 수정"
        left={back}
        right={
          <>
            <OwnerTopNav />
            <OwnerAccountButton />
          </>
        }
      />
      <ProductEditForm
        key={product.data.id}
        product={product.data}
        onSaved={() => navigate(ROUTES.ownerStore)}
      />
    </>
  );
}
