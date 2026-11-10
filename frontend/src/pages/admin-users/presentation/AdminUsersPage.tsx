import { useState } from 'react';
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router';
import {
  MembersPanel,
  UserDetailPanel,
  memberSearchString,
  readMemberSearch,
  type MemberSearch,
} from '@/features/admin';
import { ROUTES } from '@/shared/lib/routes';

// M3 회원 탭. /admin/users/:userId면 상세를 연다: PC는 우측 패널, 모바일은 상세만 (screens.md M3)
// TODO: 모바일 상세의 「← 회원 목록」은 임시 문구다.
//   왜: screens.md M3에 모바일 상세 화면 문구가 없다 (docs/design/frontend/admin.md D-7)
//   언제: 결정 후 (디자인 시스템: content.md 관리자 문구 확정)
export function AdminUsersPage() {
  const { userId } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [version, setVersion] = useState(0);
  const search = readMemberSearch((k) => params.get(k));
  const query = memberSearchString(search);
  const selectedId = userId ?? null;

  const onSearchChange = (next: MemberSearch) => {
    navigate(`${location.pathname}${memberSearchString(next)}`);
  };

  return (
    <div className="body split r">
      <div
        className={selectedId !== null ? 'dk' : undefined}
        style={{ flexDirection: 'column', minWidth: 0 }}
      >
        <MembersPanel
          search={search}
          onSearchChange={onSearchChange}
          selectedId={selectedId}
          rowHref={(id) => `${ROUTES.adminUser(id)}${query}`}
          version={version}
        />
      </div>
      {selectedId !== null ? (
        <div style={{ display: 'grid', gap: 'var(--s3)', alignContent: 'start', minWidth: 0 }}>
          <Link
            className="link mob"
            style={{ textAlign: 'left' }}
            to={`${ROUTES.adminUsers}${query}`}
          >
            ← 회원 목록
          </Link>
          <UserDetailPanel
            key={selectedId}
            userId={selectedId}
            onChanged={() => setVersion((v) => v + 1)}
          />
        </div>
      ) : null}
    </div>
  );
}
