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

  // 브라우저 기본 스타일 리셋. 크기·배치 등 시각 스타일은 CSS(.step)가 담당한다.
  const btnStyle: CSSProperties = {
    background: 'none',
    border: 'none',
    font: 'inherit',
    color: 'inherit',
    cursor: 'pointer',
    padding: 0,
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
