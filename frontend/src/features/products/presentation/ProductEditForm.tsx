import { useState, type FormEvent } from 'react';
import { primaryImage, type Product } from '@/entities/product';
import { Button, CtaBar } from '@/shared/ui';
import { useSaveProduct } from '../application/useSaveProduct';
import { useToggleProduct } from '../application/useToggleProduct';
import { diffProduct, hasChanges } from '../domain/productChanges';
import {
  productFormFromProduct,
  validateProductForm,
  type ProductFormField,
  type ProductFormInput,
} from '../domain/productForm';
import { PRODUCT_TEXT } from '../domain/productMessages';
import { ProductForm } from './ProductForm';

export function ProductEditForm(props: { product: Product; onSaved(product: Product): void }) {
  const { product, onSaved } = props;
  const [values, setValues] = useState<ProductFormInput>(() => productFormFromProduct(product));
  const [errors, setErrors] = useState<Partial<Record<ProductFormField, string>>>({});
  const [active, setActive] = useState(product.isActive);
  const save = useSaveProduct();
  const toggle = useToggleProduct();
  const saving = save.status === 'submitting';
  const toggling = toggle.status === 'pending';

  // 검증에 실패한 값은 눌러서 오류를 볼 수 있게 변경으로 본다. 통과한 값은 달라진 필드가 있을 때만 변경이다.
  const parsed = validateProductForm(values);
  const dirty = parsed.ok ? hasChanges(diffProduct(product, parsed.value)) : true;

  async function submit() {
    if (saving) return;
    const result = validateProductForm(values);
    if (!result.ok) {
      setErrors(result.errors);
      return;
    }
    setErrors({});
    const changes = diffProduct(product, result.value);
    if (!hasChanges(changes)) return;
    const saved = await save.submit(product, changes);
    if (saved !== null) onSaved(saved);
  }

  async function onToggle() {
    if (toggling) return;
    const next = await toggle.toggle({ ...product, isActive: active });
    if (next !== null) setActive(next.isActive);
  }

  function onChange(field: keyof ProductFormInput, value: string) {
    setValues((prev) => ({ ...prev, [field]: value }));
    if (field !== 'description') setErrors((prev) => ({ ...prev, [field]: undefined }));
  }

  // FIXME: 사진을 바꾸거나 지울 수 없다. 사진은 읽기 전용으로만 보인다.
  //   왜: 사용자 결정으로 이번 차수에서 사진은 보기만 한다 (docs/design/frontend/products.md §0.1 B-1, D-12)
  //   언제: 다음 차수(O11 사진 바꾸기·삭제 구현 시), 늦어도 배포 전
  const image = primaryImage(product);
  const photoSrc = image !== null && image.src !== '' ? image.src : null;

  const saveButton = (extra: { desktopOnly?: boolean }) => (
    <Button
      variant="primary"
      desktopOnly={extra.desktopOnly}
      disabled={!dirty || saving}
      pending={saving}
      onClick={() => void submit()}
    >
      {PRODUCT_TEXT.edit.save}
    </Button>
  );

  return (
    <>
      <div className="body split h">
        <form
          noValidate
          style={{ display: 'grid', gap: 'var(--s2)', alignContent: 'start' }}
          onSubmit={(e: FormEvent) => e.preventDefault()}
        >
          {save.errorMessage !== null ? (
            <div className="err" role="alert">
              {save.errorMessage}
            </div>
          ) : null}
          <ProductForm
            mode="edit"
            values={values}
            errors={errors}
            disabled={saving}
            onChange={onChange}
          />
          <div className="lbl">{PRODUCT_TEXT.edit.photoLabel}</div>
          <div className="ph photo">
            {photoSrc !== null ? (
              <img
                src={photoSrc}
                alt=""
                style={{
                  position: 'absolute',
                  inset: 0,
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  borderRadius: 'var(--r)',
                }}
              />
            ) : null}
          </div>
        </form>
        <div className="box">
          <div className="row">
            <b style={{ flex: 1 }}>{PRODUCT_TEXT.edit.visibleTitle}</b>
            <span className={active ? 'chip on' : 'chip'}>
              {active ? PRODUCT_TEXT.edit.visibleChip : PRODUCT_TEXT.edit.hiddenChip}
            </span>
          </div>
          <div className="m">{PRODUCT_TEXT.edit.hideHint}</div>
          {toggle.errorMessage !== null ? (
            <div className="err" role="alert">
              {toggle.errorMessage}
            </div>
          ) : null}
          {active ? (
            <button
              type="button"
              className="link"
              style={{
                background: 'none',
                border: 0,
                padding: 0,
                cursor: 'pointer',
                textAlign: 'left',
              }}
              aria-disabled={toggling ? 'true' : undefined}
              onClick={() => void onToggle()}
            >
              {toggling ? PRODUCT_TEXT.form.pending : PRODUCT_TEXT.edit.hide}
            </button>
          ) : (
            <Button pending={toggling} onClick={() => void onToggle()}>
              {PRODUCT_TEXT.edit.show}
            </Button>
          )}
          {saveButton({ desktopOnly: true })}
        </div>
      </div>
      <CtaBar>{saveButton({})}</CtaBar>
    </>
  );
}
