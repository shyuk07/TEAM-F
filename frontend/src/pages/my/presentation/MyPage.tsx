import { useRef, useState } from 'react';
import { Link } from 'react-router';
import {
  LogoutConfirmSheet,
  POINTS_EMPTY_MESSAGE,
  POINTS_LOAD_FAILED_MESSAGE,
  PointLogList,
  PointLogSkeleton,
  RECENT_POINT_COUNT,
  RETRY_LABEL,
  formatPoint,
  useAuth,
  usePointHistory,
} from '@/features/auth';
import { ROUTES } from '@/shared/lib/routes';
import { useModalFocus } from '@/shared/lib/useModalFocus';

// PointHistoryState 타입은 공개 API에 없어 훅 반환 타입으로 받는다.
type PointHistoryState = ReturnType<typeof usePointHistory>;

// C6 마이(+C10 로그아웃 시트). 고객 가드 안이라 user가 있다. .app·탭 바는 CustomerLayout이 그린다(customer-home.md §3.6).
export function MyPage() {
  const { state } = useAuth();
  const points = usePointHistory(RECENT_POINT_COUNT);
  const [logoutOpen, setLogoutOpen] = useState(false);
  if (state.status !== 'authenticated') return null;
  const { user } = state;

  return (
    <>
      <div className="bar">
        <h1 className="logo">마이</h1>
        <span className="sp" />
      </div>
      {logoutOpen ? (
        <LogoutDim onClose={() => setLogoutOpen(false)} />
      ) : (
        <div className="body">
          <div className="box">
            <div className="t">{user.name ?? user.email}</div>
            <div className="m">{user.email}</div>
            <div className="kv">
              <span>포인트</span>
              <b>{formatPoint(points.balance ?? user.point)}</b>
            </div>
          </div>
          <div className="list">
            <Link className="li" to={ROUTES.accountProfile} state={{ from: ROUTES.me }}>
              프로필 변경 <span className="m">›</span>
            </Link>
            <Link className="li" to={ROUTES.accountPassword} state={{ from: ROUTES.me }}>
              비밀번호 변경 <span className="m">›</span>
            </Link>
            <button type="button" className="li" onClick={() => setLogoutOpen(true)}>
              로그아웃 <span className="m">›</span>
            </button>
          </div>
          <div className="row">
            <span className="lbl" style={{ flex: 1 }}>
              최근 포인트 내역
            </span>
            <Link className="link" to={ROUTES.mePoints}>
              전체 보기
            </Link>
          </div>
          <RecentPoints points={points} />
          <Link className="link" to={ROUTES.meWithdraw}>
            회원 탈퇴
          </Link>
        </div>
      )}
    </>
  );
}

function RecentPoints({ points }: { points: PointHistoryState }) {
  switch (points.status) {
    case 'loading':
      return <PointLogSkeleton rows={RECENT_POINT_COUNT} />;
    case 'error':
      return (
        <>
          <div className="warn" role="alert">
            {POINTS_LOAD_FAILED_MESSAGE}
          </div>
          <button type="button" className="btn sm" onClick={points.retry}>
            {RETRY_LABEL}
          </button>
        </>
      );
    case 'empty':
      return <div className="m">{POINTS_EMPTY_MESSAGE}</div>;
    case 'success':
      return <PointLogList logs={points.logs} variant="short" />;
  }
}

// C10: .body 자리에 .dim + 시트. 바깥 누름·Escape → 닫힘(customer-home.md D-15, D-23).
function LogoutDim({ onClose }: { onClose(): void }) {
  const dimRef = useRef<HTMLDivElement>(null);
  useModalFocus(dimRef, onClose);
  return (
    <div
      className="dim"
      ref={dimRef}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <LogoutConfirmSheet onClose={onClose} />
    </div>
  );
}
