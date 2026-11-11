import type { CSSProperties, MouseEventHandler, ReactNode } from 'react';

export type ButtonProps = {
  variant?: 'default' | 'primary' | 'dark';
  size?: 'md' | 'sm';
  pending?: boolean;
  disabled?: boolean;
  desktopOnly?: boolean;
  type?: 'button' | 'submit';
  form?: string;
  onClick?: MouseEventHandler<HTMLButtonElement>;
  style?: CSSProperties;
  children: ReactNode;
};

export function Button({
  variant,
  size,
  pending,
  disabled,
  desktopOnly,
  type = 'button',
  form,
  onClick,
  style,
  children,
}: ButtonProps) {
  const blocked = pending === true || disabled === true;
  const cls = [
    'btn',
    variant === 'primary' ? 'pri' : variant === 'dark' ? 'dark' : '',
    size === 'sm' ? 'sm' : '',
    desktopOnly ? 'dk' : '',
  ]
    .filter(Boolean)
    .join(' ');

  const handleClick: MouseEventHandler<HTMLButtonElement> = (e) => {
    if (blocked) {
      // disabled·pending 중에는 클릭과 폼 제출(submit type)을 모두 막는다.
      e.preventDefault();
      e.stopPropagation();
      return;
    }
    onClick?.(e);
  };

  return (
    <button
      type={type}
      className={cls}
      form={form}
      style={style}
      aria-disabled={blocked ? 'true' : undefined}
      onClick={handleClick}
    >
      {pending ? '처리 중…' : children}
    </button>
  );
}
