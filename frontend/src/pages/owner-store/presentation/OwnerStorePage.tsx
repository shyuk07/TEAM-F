import { Link } from 'react-router';
import { storeStatusLabel, storeStatusTone, useOwnerStore } from '@/entities/store';
import { ProductList } from '@/features/products';
import { ROUTES } from '@/shared/lib/routes';
import { AppBar, Box, StatusTag } from '@/shared/ui';
import { OwnerAccountButton, OwnerAccountRows, OwnerTopNav } from '@/widgets/owner-nav';

// O4 매장·상품(products.md §5.1). 상점 정보 + 상품 목록 + 계정 행 + 상점 폐점 링크.
export function OwnerStorePage() {
  const store = useOwnerStore();

  if (store === null) return null;

  return (
    <>
      <AppBar
        logo
        title="매장"
        right={
          <>
            <OwnerTopNav />
            <OwnerAccountButton />
          </>
        }
      />
      <div className="body split">
        <Box title={store.name}>
          <div className="m">{store.pickupAddress}</div>
          <div>
            <StatusTag tone={storeStatusTone(store.status)}>
              {storeStatusLabel(store.status)}
            </StatusTag>
          </div>
        </Box>
        <div style={{ display: 'grid', gap: 'var(--s3)', alignContent: 'start' }}>
          <ProductList storeId={store.id} />
          <OwnerAccountRows />
          <div>
            <Link className="link" to={ROUTES.ownerStoreClose}>
              상점 폐점
            </Link>
          </div>
        </div>
      </div>
    </>
  );
}
