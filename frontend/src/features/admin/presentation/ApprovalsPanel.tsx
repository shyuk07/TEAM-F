import { useId, useState, type FormEvent } from 'react';
import { useUserList } from '../application/useAdminQueries';
import { useAdminMutation } from '../application/useAdminMutation';
import type { AdminUserSummary } from '../domain/adminUser';
import { displayName } from '../domain/labels';
import { APPROVAL_FILTER, PAGE_SIZE, normalizeEmailSearch, pageSummary } from '../domain/userQuery';
import { ListSkeleton, LoadError } from './LoadStates';
import { Pager } from './Pager';
import { SanctionSheet } from './SanctionSheet';
import { ApprovalTable } from './UserTable';

// TODO: 빈 목록 문구 「승인 대기 중인 상점주가 없어요」는 임시 문구다.
//   왜: screens.md M1에 빈 상태 문구가 없다 (docs/design/frontend/admin.md D-7)
//   언제: 결정 후 (디자인 시스템: content.md 관리자 빈 상태 문구 확정)
// open-issues: M1 「정지 상점」 건수는 상점 목록 API가 없어 보여 주지 않는다 (admin.md C-3, D-3)
export function ApprovalsPanel() {
  const searchId = useId();
  const [searchText, setSearchText] = useState('');
  const [email, setEmail] = useState<string | undefined>(undefined);
  const [page, setPage] = useState(1);
  const [version, setVersion] = useState(0);
  const [rejecting, setRejecting] = useState<AdminUserSummary | null>(null);
  const approve = useAdminMutation();

  const list = useUserList({ ...APPROVAL_FILTER, email, page, size: PAGE_SIZE }, version);
  const pendingCount = useUserList({ ...APPROVAL_FILTER, page: 1, size: 1 }, version);
  const suspendedCount = useUserList({ status: 'SUSPENDED', page: 1, size: 1 }, version);

  const refresh = () => setVersion((v) => v + 1);

  function onSearch(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setEmail(normalizeEmailSearch(searchText));
    setPage(1);
  }

  async function onApprove(u: AdminUserSummary) {
    const outcome = await approve.run((admin) => admin.approveOwner(u.id));
    if (outcome.ok) refresh();
  }

  return (
    <div className="body split">
      <div className="box">
        <form role="search" onSubmit={onSearch}>
          <label className="lbl" htmlFor={searchId} hidden>
            이메일로 회원 검색
          </label>
          <input
            id={searchId}
            className="in"
            type="search"
            placeholder="이메일로 회원 검색"
            style={{ width: '100%', color: 'var(--fg)' }}
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
          />
        </form>
        <div className="kv">
          <span>승인 대기</span>
          <b className="cd">{pendingCount.status === 'success' ? pendingCount.data.total : '–'}</b>
        </div>
        <div className="kv">
          <span>정지 회원</span>
          <b>{suspendedCount.status === 'success' ? suspendedCount.data.total : '–'}</b>
        </div>
      </div>
      <div style={{ display: 'grid', gap: 'var(--s3)', minWidth: 0, alignContent: 'start' }}>
        {approve.error !== null ? (
          <div className="err" role="alert">
            {approve.error}
          </div>
        ) : null}
        {list.status === 'loading' ? <ListSkeleton /> : null}
        {list.status === 'error' ? <LoadError error={list.error} onRetry={list.reload} /> : null}
        {list.status === 'success' && list.data.items.length === 0 ? (
          <div className="box empty">
            <div className="ic"></div>
            <b>승인 대기 중인 상점주가 없어요</b>
          </div>
        ) : null}
        {list.status === 'success' && list.data.items.length === 0 && page > 1 ? (
          <Pager
            summary={pageSummary(page, list.data.size, list.data.total)}
            onPrev={() => setPage((p) => Math.max(1, p - 1))}
            onNext={() => setPage((p) => p + 1)}
          />
        ) : null}
        {list.status === 'success' && list.data.items.length > 0 ? (
          <>
            <ApprovalTable
              users={list.data.items}
              pending={approve.pending}
              onApprove={(u) => void onApprove(u)}
              onReject={setRejecting}
            />
            <Pager
              summary={pageSummary(list.data.page, list.data.size, list.data.total)}
              onPrev={() => setPage((p) => Math.max(1, p - 1))}
              onNext={() => setPage((p) => p + 1)}
            />
          </>
        ) : null}
      </div>
      {rejecting !== null ? (
        <SanctionSheet
          kind="rejectOwner"
          target={{ id: rejecting.id, label: `${displayName(rejecting)} (${rejecting.email})` }}
          onClose={() => setRejecting(null)}
          onDone={() => {
            setRejecting(null);
            refresh();
          }}
        />
      ) : null}
    </div>
  );
}
