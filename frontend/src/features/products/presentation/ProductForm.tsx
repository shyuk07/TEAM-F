import { useId } from 'react';
import { FieldError } from '@/shared/ui';
import type { ProductFormField, ProductFormInput } from '../domain/productForm';
import { PRODUCT_TEXT } from '../domain/productMessages';

// 내부 부품: 입력 4칸만 그린다. 값·오류·제출은 부모가 한다(products.md D-30).
export function ProductForm(props: {
  mode: 'create' | 'edit';
  values: ProductFormInput;
  errors: Partial<Record<ProductFormField, string>>;
  disabled?: boolean;
  onChange(field: keyof ProductFormInput, value: string): void;
}) {
  const { mode, values, errors, disabled, onChange } = props;
  const text = PRODUCT_TEXT[mode];
  const ids = { name: useId(), price: useId(), category: useId(), description: useId() };

  return (
    <>
      <Field id={ids.name} label={text.nameLabel} error={errors.name}>
        <input
          id={ids.name}
          className="in"
          type="text"
          value={values.name}
          disabled={disabled}
          aria-invalid={errors.name ? 'true' : undefined}
          aria-describedby={errors.name ? `${ids.name}-error` : undefined}
          onChange={(e) => onChange('name', e.target.value)}
        />
      </Field>
      <Field id={ids.price} label={text.priceLabel} error={errors.price}>
        <input
          id={ids.price}
          className="in"
          type="text"
          inputMode="numeric"
          value={values.price}
          disabled={disabled}
          aria-invalid={errors.price ? 'true' : undefined}
          aria-describedby={errors.price ? `${ids.price}-error` : undefined}
          onChange={(e) => onChange('price', e.target.value)}
        />
      </Field>
      <Field id={ids.category} label={text.categoryLabel} error={errors.category}>
        <input
          id={ids.category}
          className="in"
          type="text"
          value={values.category}
          disabled={disabled}
          aria-invalid={errors.category ? 'true' : undefined}
          aria-describedby={errors.category ? `${ids.category}-error` : undefined}
          onChange={(e) => onChange('category', e.target.value)}
        />
      </Field>
      <Field id={ids.description} label={text.descriptionLabel}>
        <textarea
          id={ids.description}
          className="in"
          style={{ minHeight: 64 }}
          value={values.description}
          disabled={disabled}
          onChange={(e) => onChange('description', e.target.value)}
        />
      </Field>
    </>
  );
}

function Field(props: { id: string; label: string; error?: string; children: React.ReactNode }) {
  const { id, label, error, children } = props;
  return (
    <div>
      <label className="lbl" htmlFor={id}>
        {label}
      </label>
      {children}
      {error ? <FieldError id={`${id}-error`}>{error}</FieldError> : null}
    </div>
  );
}
