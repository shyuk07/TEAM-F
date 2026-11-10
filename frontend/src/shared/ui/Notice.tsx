import type { ReactNode } from 'react';

export type NoticeProps = {
  children: ReactNode;
};

export function Notice({ children }: NoticeProps) {
  return <div className="warn">{children}</div>;
}
