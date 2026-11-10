import { Link } from 'react-router';
import { BACK_LABEL, WithdrawForm, useAuth, usePointHistory } from '@/features/auth';
import { ROUTES } from '@/shared/lib/routes';

// C7 회원 탈퇴 확인. 잔액만 쓰려고 포인트 1건을 받는다. .app은 CustomerLayout이 그린다(customer-home.md §3.6).
// TODO: 탈퇴 뒤 안내 없이 홈으로 보낸다.
//   왜: 탈퇴 완료 뒤 화면·문구가 정본에 없고 알림 컴포넌트도 없다 (customer-home.md C-15)
//   언제: 결정 후 (디자인 시스템: 탈퇴 완료 안내)
export function WithdrawPage() {
  const { state } = useAuth();
  const points = usePointHistory(1);
  if (state.status !== 'authenticated') return null;

  return (
    <>
      <div className="bar">
        <Link to={ROUTES.me} aria-label={BACK_LABEL}>
          ←
        </Link>
        <h1 className="t">회원 탈퇴</h1>
        <span className="sp" />
      </div>
      <WithdrawForm balance={points.balance ?? state.user.point} cancelTo={ROUTES.me} />
    </>
  );
}
