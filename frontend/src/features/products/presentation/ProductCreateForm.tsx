import { useRef, useState, type FormEvent } from 'react';
import type { Product } from '@/entities/product';
import { Button, CtaBar } from '@/shared/ui';
import { useCreateProduct } from '../application/useCreateProduct';
import { usePhotoDraft } from '../application/usePhotoDraft';
import {
  validateProductForm,
  type ProductFormField,
  type ProductFormInput,
} from '../domain/productForm';
import { PRODUCT_TEXT } from '../domain/productMessages';
import { photoSlotPhase } from '../domain/productPhoto';
import { PhotoField } from './PhotoField';
import { ProductForm } from './ProductForm';

type Intent = 'offer' | 'list';

const EMPTY: ProductFormInput = { name: '', price: '', category: '', description: '' };

// open-issues: O12 사진 1장 제한은 화면에서만 지킨다 (백엔드 제한 없음)
export function ProductCreateForm(props: {
  storeId: string;
  onCreated(product: Product, intent: Intent): void;
}) {
  const { storeId, onCreated } = props;
  const [values, setValues] = useState<ProductFormInput>(EMPTY);
  const [errors, setErrors] = useState<Partial<Record<ProductFormField, string>>>({});
  const create = useCreateProduct();
  const photo = usePhotoDraft();
  const lastIntent = useRef<Intent>('offer');
  const submitting = create.status === 'submitting';

  async function submit(intent: Intent) {
    if (submitting) return;
    lastIntent.current = intent;
    const result = validateProductForm(values);
    if (!result.ok) {
      setErrors(result.errors);
      return;
    }
    setErrors({});
    const product = await create.submit(storeId, result.value, photo.file);
    if (product !== null) onCreated(product, intent);
  }

  function onChange(field: keyof ProductFormInput, value: string) {
    setValues((prev) => ({ ...prev, [field]: value }));
    if (field !== 'description') setErrors((prev) => ({ ...prev, [field]: undefined }));
  }

  const photoMessage = submitting
    ? null
    : (photo.error ?? (create.photoError ? create.errorMessage : null));
  const phase = photoSlotPhase({
    hasImage: photo.previewSrc !== null,
    uploading: submitting,
    error: photoMessage,
  });
  // 사진 오류는 사진 칸에 보이므로 폼 위에는 그 밖의 오류만 보인다.
  const formError = create.photoError ? null : create.errorMessage;

  function onPick(file: File) {
    create.reset();
    photo.pick(file);
  }

  const submitButtons = (
    <>
      <Button
        style={{ flex: '0 0 auto' }}
        disabled={submitting}
        pending={submitting}
        onClick={() => void submit('list')}
      >
        {PRODUCT_TEXT.create.submitList}
      </Button>
      <Button
        variant="primary"
        disabled={submitting}
        pending={submitting}
        onClick={() => void submit('offer')}
      >
        {PRODUCT_TEXT.create.submitOffer}
      </Button>
    </>
  );

  return (
    <>
      <div className="body split h">
        <form
          noValidate
          style={{ display: 'grid', gap: 'var(--s2)', alignContent: 'start' }}
          onSubmit={(e: FormEvent) => e.preventDefault()}
        >
          {formError !== null ? (
            <div className="err" role="alert">
              {formError}
            </div>
          ) : null}
          <ProductForm
            mode="create"
            values={values}
            errors={errors}
            disabled={submitting}
            onChange={onChange}
          />
        </form>
        <div style={{ display: 'grid', gap: 'var(--s2)', alignContent: 'start' }}>
          <div className="lbl">{PRODUCT_TEXT.create.photoLabel}</div>
          <PhotoField
            phase={phase}
            src={photo.previewSrc}
            errorMessage={photoMessage}
            hasImage={photo.previewSrc !== null}
            disabled={submitting}
            onPick={onPick}
            onRemove={() => {
              create.reset();
              photo.clear();
            }}
            onRetry={
              photo.error === null && create.photoError
                ? () => void submit(lastIntent.current)
                : undefined
            }
          />
          <div className="m">{PRODUCT_TEXT.create.photoHint}</div>
          <Button
            desktopOnly
            disabled={submitting}
            pending={submitting}
            onClick={() => void submit('list')}
          >
            {PRODUCT_TEXT.create.submitList}
          </Button>
          <Button
            variant="primary"
            desktopOnly
            disabled={submitting}
            pending={submitting}
            onClick={() => void submit('offer')}
          >
            {PRODUCT_TEXT.create.submitOffer}
          </Button>
        </div>
      </div>
      <CtaBar>{submitButtons}</CtaBar>
    </>
  );
}
