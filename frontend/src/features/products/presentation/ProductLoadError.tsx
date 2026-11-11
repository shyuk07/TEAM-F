import { Link } from 'react-router';
import { ROUTES } from '@/shared/lib/routes';
import { Button } from '@/shared/ui';
import { PRODUCT_TEXT, type ProductLoadFailure } from '../domain/productMessages';

// 상품 불러오기 오류 표시. 구분·문구는 useProduct의 failure가 정하고 여기서는 그리기만 한다(D-35).
export function ProductLoadError(props: { failure: ProductLoadFailure; onRetry(): void }) {
  const { failure, onRetry } = props;
  return (
    <>
      <div className="err" role="alert">
        {failure.message}
      </div>
      {failure.kind === 'notFound' ? (
        <Link className="link" to={ROUTES.ownerStore}>
          {PRODUCT_TEXT.edit.toStore}
        </Link>
      ) : (
        <Button onClick={onRetry}>{PRODUCT_TEXT.edit.retry}</Button>
      )}
    </>
  );
}
