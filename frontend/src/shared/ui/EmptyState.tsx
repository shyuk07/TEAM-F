import type { ReactNode } from 'react';

export type EmptyStateProps = {
  title: string;
  description?: string;
  action?: ReactNode;
};

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="box empty">
      <div className="ic" />
      <b>{title}</b>
      {description ? <span className="m">{description}</span> : null}
      {action}
    </div>
  );
}
