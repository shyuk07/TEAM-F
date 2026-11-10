import type { AdminAccountStatus } from '../domain/adminUser';
import { accountStatusView, type StatusView } from '../domain/labels';

// 관리자 화면은 상태 문구 옆에 코드를 함께 보인다 (screens.md 「관리자 · 상태 코드 병기」)
export function StatusWithCode({
  view,
  code,
  className,
}: {
  view: StatusView;
  code: string;
  className?: string;
}) {
  const cls = [className, view.tone !== null ? `tag ${view.tone}` : null]
    .filter((c) => c !== undefined && c !== null)
    .join(' ');
  return (
    <span className={cls === '' ? undefined : cls}>
      {view.text} <span className="code-tag">{code}</span>
    </span>
  );
}

export function AccountStatusTag({
  status,
  className,
}: {
  status: AdminAccountStatus;
  className?: string;
}) {
  return <StatusWithCode view={accountStatusView(status)} code={status} className={className} />;
}
