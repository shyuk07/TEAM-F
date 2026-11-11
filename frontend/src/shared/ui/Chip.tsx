import type { CSSProperties, MouseEventHandler, ReactNode } from 'react';

export type ChipProps = {
  selected?: boolean;
  disabled?: boolean;
  onClick?: MouseEventHandler<HTMLButtonElement>;
  style?: CSSProperties;
  className?: string;
  'aria-label'?: string;
  children: ReactNode;
};

export function Chip({
  selected,
  disabled,
  onClick,
  style,
  className,
  'aria-label': ariaLabel,
  children,
}: ChipProps) {
  const cls = ['chip', selected ? 'on' : '', className ?? ''].filter(Boolean).join(' ');

  return (
    <button
      type="button"
      className={cls}
      disabled={disabled}
      aria-pressed={selected ? 'true' : 'false'}
      aria-label={ariaLabel}
      onClick={onClick}
      style={style}
    >
      {children}
    </button>
  );
}
