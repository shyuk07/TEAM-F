import type { ReactNode } from 'react';

export type BoxProps = {
  tag?: ReactNode;
  title?: string;
  tone?: 'default' | 'done';
  children?: ReactNode;
};

export function Box({ tag, title, tone, children }: BoxProps) {
  return (
    <div className={tone === 'done' ? 'box done' : 'box'}>
      {tag}
      {title !== undefined ? <div className="t">{title}</div> : null}
      {children}
    </div>
  );
}
