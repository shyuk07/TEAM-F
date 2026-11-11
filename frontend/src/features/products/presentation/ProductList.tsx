import { Link } from 'react-router';
import { readErrorInfo } from '@/shared/lib/errorInfo';
import { ROUTES } from '@/shared/lib/routes';
import { Button, EmptyState, Skeleton } from '@/shared/ui';
import { useStoreProducts } from '../application/useStoreProducts';
import { PRODUCT_TEXT, productCountLabel, productErrorMessage } from '../domain/productMessages';
import { ProductRow } from './ProductRow';

export function ProductList({ storeId }: { storeId: string }) {
  const products = useStoreProducts(storeId);

  if (products.status === 'loading') {
    return (
      <div className="list">
        <Skeleton />
        <Skeleton />
        <Skeleton />
      </div>
    );
  }

  if (products.status === 'error') {
    return (
      <div className="list">
        <div className="err" role="alert">
          {productErrorMessage(readErrorInfo(products.error), 'load')}
        </div>
        <Button onClick={products.reload}>{PRODUCT_TEXT.list.retry}</Button>
      </div>
    );
  }

  const { items, total } = products.data;

  if (total === 0) {
    return (
      <EmptyState
        title={PRODUCT_TEXT.list.emptyTitle}
        description={PRODUCT_TEXT.list.emptyDescription}
        action={
          <Link className="btn sm" to={ROUTES.ownerProductNew}>
            {PRODUCT_TEXT.list.emptyAction}
          </Link>
        }
      />
    );
  }

  return (
    <div className="list">
      <div className="row">
        <span className="lbl" style={{ flex: 1 }}>
          {productCountLabel(total)}
        </span>
        <Link className="btn sm" to={ROUTES.ownerProductNew}>
          {PRODUCT_TEXT.list.add}
        </Link>
      </div>
      {items.map((product) => (
        <ProductRow key={product.id} product={product} />
      ))}
    </div>
  );
}
