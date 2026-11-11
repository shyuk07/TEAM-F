import type { CSSProperties } from 'react';

export type StepperProps = {
  value: number;
  min?: number;
  max?: number;
  step?: number;
  disabled?: boolean;
  onChange?: (next: number) => void;
  minusLabel?: string;
  plusLabel?: string;
  style?: CSSProperties;
  className?: string;
};

export function Stepper({
  value,
  min = 1,
  max = 9999,
  step = 1,
  disabled,
  onChange,
  minusLabel = '수량 감소',
  plusLabel = '수량 증가',
  style,
  className,
}: StepperProps) {
  const canMinus = !disabled && value > min;
  const canPlus = !disabled && value < max;

  const handleMinus = () => {
    if (!canMinus) return;
    const next = Math.max(min, value - step);
    onChange?.(next);
  };

  const handlePlus = () => {
    if (!canPlus) return;
    const next = Math.min(max, value + step);
    onChange?.(next);
  };

  const btnStyle: CSSProperties = {
    background: 'none',
    border: 'none',
    padding: 0,
    font: 'inherit',
    color: 'inherit',
    cursor: 'pointer',
    fontSize: '18px',
    lineHeight: 1,
    userSelect: 'none',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
  };

  const disabledBtnStyle: CSSProperties = {
    ...btnStyle,
    opacity: 0.3,
    cursor: 'default',
  };

  return (
    <div className={['step', className ?? ''].filter(Boolean).join(' ')} style={style}>
      <button
        type="button"
        aria-label={minusLabel}
        disabled={!canMinus}
        onClick={handleMinus}
        style={canMinus ? btnStyle : disabledBtnStyle}
      >
        −
      </button>
      <b>{value}</b>
      <button
        type="button"
        aria-label={plusLabel}
        disabled={!canPlus}
        onClick={handlePlus}
        style={canPlus ? btnStyle : disabledBtnStyle}
      >
        +
      </button>
    </div>
  );
}
