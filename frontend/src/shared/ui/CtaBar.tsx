import type { ReactNode } from 'react';

export type CtaBarProps = {
  children: ReactNode;
};

export function CtaBar({ children }: CtaBarProps) {
  return <div className="cta">{children}</div>;
}
