import { Link } from 'react-router';
import type { AdminUserSummary } from '../domain/adminUser';
import { displayName, formatShortDate } from '../domain/labels';
import { canReview } from '../domain/userActions';
import { AccountStatusTag } from './AccountStatusTag';

const ROW_LINK_STYLE = { color: 'inherit', textDecoration: 'none' } as const;

function Header({ first, second }: { first: string; second: string }) {
  return (
    <div className="tr th">
      <span className="lbl">{first}</span>
      <span className="lbl">{second}</span>
      <span className="lbl">가입일</span>
      <span className="lbl">상태</span>
      <span></span>
    </div>
  );
}

// M1 승인 표: 상점주(상호) · 이메일 · 가입일 · 상태 · 「승인」「거부」
export function ApprovalTable({
  users,
  pending,
  onApprove,
  onReject,
}: {
  users: AdminUserSummary[];
  pending: boolean;
  onApprove(u: AdminUserSummary): void;
  onReject(u: AdminUserSummary): void;
}) {
  return (
    <div className="list">
      <Header first="상점주(상호)" second="이메일" />
      {users.map((u) => (
        <div className="tr" key={u.id}>
          <div>
            <b>{displayName(u)}</b>
            <div className="m mob">{`${u.email} · ${formatShortDate(u.createdAt)}`}</div>
          </div>
          <span className="hide">{u.email}</span>
          <span className="hide">{formatShortDate(u.createdAt)}</span>
          <AccountStatusTag status={u.status} className="hide" />
          {canReview(u) ? (
            <span className="row">
              <button
                type="button"
                className="btn sm"
                aria-disabled={pending ? 'true' : undefined}
                aria-label={`${displayName(u)} 승인`}
                onClick={() => {
                  if (!pending) onApprove(u);
                }}
              >
                승인
              </button>
              <button
                type="button"
                className="btn sm"
                aria-label={`${displayName(u)} 거부`}
                aria-disabled={pending ? 'true' : undefined}
                onClick={() => {
                  if (!pending) onReject(u);
                }}
              >
                거부
              </button>
            </span>
          ) : (
            <span></span>
          )}
        </div>
      ))}
    </div>
  );
}

// M3 회원 표: 이름 · 이메일 · 역할 · 가입일 · 상태 · ›  (행을 누르면 상세)
export function MemberTable({
  users,
  selectedId,
  rowHref,
}: {
  users: AdminUserSummary[];
  selectedId: string | null;
  rowHref(id: string): string;
}) {
  return (
    <div className="list">
      <Header first="이름 · 이메일" second="역할" />
      {users.map((u) => {
        const selected = u.id === selectedId;
        return (
          <Link
            key={u.id}
            to={rowHref(u.id)}
            className={selected ? 'tr sel' : 'tr'}
            style={ROW_LINK_STYLE}
            aria-current={selected ? 'true' : undefined}
          >
            <div>
              <b>{displayName(u)}</b>
              <div className="m">{u.email}</div>
            </div>
            <span className="hide">{u.role}</span>
            <span className="hide">{formatShortDate(u.createdAt)}</span>
            <AccountStatusTag status={u.status} className="hide" />
            <b className="m" aria-hidden="true">
              ›
            </b>
          </Link>
        );
      })}
    </div>
  );
}
