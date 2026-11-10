import { Link } from 'react-router';
import {
  BACK_LABEL,
  POINTS_EMPTY_MESSAGE,
  POINTS_LOAD_FAILED_MESSAGE,
  POINT_PAGE_SIZE,
  PointLogList,
  PointLogSkeleton,
  RETRY_LABEL,
  formatPoint,
  useAuth,
  usePointHistory,
} from '@/features/auth';
import { ROUTES } from '@/shared/lib/routes';

type PointHistoryState = ReturnType<typeof usePointHistory>;

// C11 포인트 내역 전체. 하위 화면이라 탭 바 없음. .app은 CustomerLayout이 그린다(customer-home.md §3.6).
export function PointHistoryPage() {
  const { state } = useAuth();
  const points = usePointHistory(POINT_PAGE_SIZE);
  if (state.status !== 'authenticated') return null;

  return (
    <>
      <div className="bar">
        <Link to={ROUTES.me} aria-label={BACK_LABEL}>
          ←
        </Link>
        <h1 className="t">포인트</h1>
        <span className="sp" />
      </div>
      <div className="body">
        <div className="box" style={{ background: 'var(--fill)' }}>
          <div className="lbl">보유 포인트</div>
          <b style={{ fontSize: 22 }}>{formatPoint(points.balance ?? state.user.point)}</b>
          <div className="m">결제 금액의 1% 적립 · 100P 단위로 사용</div>
        </div>
        <PointLogs points={points} />
      </div>
    </>
  );
}

function PointLogs({ points }: { points: PointHistoryState }) {
  switch (points.status) {
    case 'loading':
      return <PointLogSkeleton rows={5} />;
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
      return (
        <div className="box empty">
          <div className="ic" />
          <b>{POINTS_EMPTY_MESSAGE}</b>
          <Link className="btn sm" to={ROUTES.home}>
            할인 보러 가기
          </Link>
        </div>
      );
    case 'success':
      return (
        <>
          <PointLogList logs={points.logs} variant="full" />
          {points.loadMoreFailed ? (
            <div className="warn" role="alert">
              {POINTS_LOAD_FAILED_MESSAGE}
            </div>
          ) : null}
          {points.hasMore ? (
            <button
              type="button"
              className="link"
              aria-disabled={points.loadingMore ? 'true' : undefined}
              onClick={points.loadMore}
            >
              {points.loadingMore ? '처리 중…' : '더 보기'}
            </button>
          ) : null}
        </>
      );
  }
}
