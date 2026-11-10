import { Link, Navigate, useLocation } from 'react-router';
import { LoginForm, readFrom, resolvePostLoginPath, useAuth } from '@/features/auth';
import { ROUTES } from '@/shared/lib/routes';

// TODO: 「회원가입」 버튼과 「비밀번호 재설정」·「입점 신청」 링크가 이동하지 않는다.
//   왜: 도착 화면 A2·A3가 아직 없다 (docs/design/frontend/auth.md §3.4, D-10)
//   언제: A2 구현 시, A3 구현 시, 늦어도 배포 전
// TODO: 진입 경로별 안내 한 줄(예약을 이어가려면…)이 없다.
//   왜: 고객 흐름(C2·내 예약 탭)이 없어 진입 경로를 구분할 수 없다 (screens.md A1 동작 메모)
//   언제: C2 구현 시
export function LoginPage() {
  const { state } = useAuth();
  const location = useLocation();

  if (state.status === 'authenticated') {
    return <Navigate replace to={resolvePostLoginPath(state.user, readFrom(location.state))} />;
  }
  if (state.status === 'loading') return <div className="app" aria-busy="true" />;

  return (
    <div className="app">
      <div className="bar">
        <Link to={ROUTES.home} aria-label="닫기">
          ✕
        </Link>
        <span className="sp"></span>
      </div>
      <div className="body">
        <h1>로그인</h1>
        <LoginForm />
        <span className="link">비밀번호 재설정</span>
      </div>
      <div
        className="cta"
        style={{ flexDirection: 'column', alignItems: 'stretch', gap: 'var(--s2)' }}
      >
        <span className="m" style={{ textAlign: 'center' }}>
          계정이 없나요?
        </span>
        <button type="button" className="btn">
          회원가입
        </button>
        <span className="link">사장님이신가요? 입점 신청</span>
      </div>
    </div>
  );
}
