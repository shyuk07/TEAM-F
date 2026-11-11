import { Link } from 'react-router';
import {
  productStatusLabel,
  productStatusTone,
  productSubtitle,
  type Product,
} from '@/entities/product';
import { ROUTES } from '@/shared/lib/routes';
import { StatusTag } from '@/shared/ui';

export function ProductRow({ product }: { product: Product }) {
  return (
    <Link className="li" to={ROUTES.ownerProduct(product.id)}>
      <div>
        <b>{product.name}</b>
        <div className="m">{productSubtitle(product)}</div>
      </div>
      <StatusTag tone={productStatusTone(product)}>{productStatusLabel(product)}</StatusTag>
    </Link>
  );
}
