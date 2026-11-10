import type { ReactNode } from 'react';

export type AppBarProps = {
  title: string;
  logo?: boolean;
  left?: ReactNode;
  right?: ReactNode;
};

export function AppBar({ title, logo, left, right }: AppBarProps) {
  return (
    <div className="bar">
      {left}
      <span className={logo ? 'logo' : 't'}>{title}</span>
      <span className="sp" />
      {right}
    </div>
  );
}
