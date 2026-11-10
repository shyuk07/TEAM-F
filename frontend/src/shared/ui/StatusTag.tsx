import type { ReactNode } from 'react';

export type StatusTagProps = {
  tone: 'ok' | 'hot' | 'mute';
  children: ReactNode;
};

export function StatusTag({ tone, children }: StatusTagProps) {
  return <span className={`tag ${tone}`}>{children}</span>;
}
