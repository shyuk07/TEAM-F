import { useId, useState, type FormEvent } from 'react';
import { useUserList } from '../application/useAdminQueries';
import {
  MEMBER_FILTERS,
  memberListQuery,
  pageSummary,
  type MemberSearch,
} from '../domain/userQuery';
import { ListSkeleton, LoadError } from './LoadStates';
import { Pager } from './Pager';
import { MemberTable } from './UserTable';

// TODO: 빈 목록 문구 「조건에 맞는 회원이 없어요」는 임시 문구다.
//   왜: screens.md M3에 빈 상태 문구가 없다 (docs/design/frontend/admin.md D-7)
//   언제: 결정 후 (디자인 시스템: content.md 관리자 빈 상태 문구 확정)
export function MembersPanel({
  search,
  onSearchChange,
  selectedId,
  rowHref,
  version,
}: {
  search: MemberSearch;
  onSearchChange(next: MemberSearch): void;
  selectedId: string | null;
  rowHref(id: string): string;
  version: number;
}) {
  const list = useUserList(memberListQuery(search), version);

  return (
    <div style={{ display: 'grid', gap: 'var(--s3)', minWidth: 0, alignContent: 'start' }}>
      <EmailSearch
        key={search.email}
        initial={search.email}
        onSubmit={(email) => onSearchChange({ ...search, email, page: 1 })}
      />
      <div className="scroll" role="group" aria-label="회원 필터">
        {MEMBER_FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            className={f.key === search.filter ? 'chip on' : 'chip'}
            aria-pressed={f.key === search.filter}
            onClick={() => onSearchChange({ ...search, filter: f.key, page: 1 })}
          >
            {f.label}
          </button>
        ))}
      </div>
      {list.status === 'loading' ? <ListSkeleton /> : null}
      {list.status === 'error' ? <LoadError error={list.error} onRetry={list.reload} /> : null}
      {list.status === 'success' && list.data.items.length === 0 ? (
        <div className="box empty">
          <div className="ic"></div>
          <b>조건에 맞는 회원이 없어요</b>
        </div>
      ) : null}
      {list.status === 'success' && list.data.items.length === 0 && search.page > 1 ? (
        <Pager
          summary={pageSummary(search.page, list.data.size, list.data.total)}
          onPrev={() => onSearchChange({ ...search, page: Math.max(1, search.page - 1) })}
          onNext={() => onSearchChange({ ...search, page: search.page + 1 })}
        />
      ) : null}
      {list.status === 'success' && list.data.items.length > 0 ? (
        <>
          <MemberTable users={list.data.items} selectedId={selectedId} rowHref={rowHref} />
          <Pager
            summary={pageSummary(list.data.page, list.data.size, list.data.total)}
            onPrev={() => onSearchChange({ ...search, page: Math.max(1, search.page - 1) })}
            onNext={() => onSearchChange({ ...search, page: search.page + 1 })}
          />
        </>
      ) : null}
    </div>
  );
}

// 주소의 검색어가 바뀌면(뒤로 가기 등) key가 바뀌어 입력칸을 새 값으로 다시 만든다.
function EmailSearch({ initial, onSubmit }: { initial: string; onSubmit(email: string): void }) {
  const searchId = useId();
  const [text, setText] = useState(initial);
  return (
    <form
      role="search"
      onSubmit={(e: FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        onSubmit(text.trim());
      }}
    >
      <label className="lbl" htmlFor={searchId} hidden>
        이메일로 검색
      </label>
      <input
        id={searchId}
        className="in"
        type="search"
        placeholder="이메일로 검색"
        style={{ width: '100%', color: 'var(--fg)' }}
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
    </form>
  );
}
