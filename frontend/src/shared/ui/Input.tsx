import { useId } from 'react';
import type { HTMLInputTypeAttribute, ReactNode } from 'react';
import { FieldError } from './FieldError';

export type InputProps = {
  label: ReactNode;
  value: string;
  onChange(value: string): void;
  type?: HTMLInputTypeAttribute;
  autoComplete?: string;
  maxLength?: number;
  required?: boolean;
  readOnly?: boolean;
  error?: string | null;
  id?: string;
};

export function Input({
  label,
  value,
  onChange,
  type,
  autoComplete,
  maxLength,
  required,
  readOnly,
  error,
  id,
}: InputProps) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const errorId = error ? `${inputId}-error` : undefined;

  return (
    <div>
      <label className="lbl" htmlFor={inputId}>
        {label}
        {required ? ' *' : null}
      </label>
      <input
        id={inputId}
        className={readOnly ? 'in ro' : 'in'}
        type={type}
        value={value}
        autoComplete={autoComplete}
        maxLength={maxLength}
        readOnly={readOnly}
        aria-invalid={error ? 'true' : undefined}
        aria-describedby={errorId}
        onChange={(e) => onChange(e.target.value)}
      />
      {error ? <FieldError id={errorId}>{error}</FieldError> : null}
    </div>
  );
}
