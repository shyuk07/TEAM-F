import { Link, Navigate, useLocation, useNavigate } from 'react-router';
import {
  BACK_LABEL,
  SignupForm,
  readFrom,
  readSignupRole,
  resolvePostLoginPath,
  useAuth,
} from '@/features/auth';
import { ROUTES } from '@/shared/lib/routes';

// TODO: C2에서 가입하러 왔을 때 같은 수량으로 예약을 이어가지 않는다(원래 화면으로만 돌아간다).
//   왜: 고객 흐름(C2)이 없다 (screens.md A2 동작 메모)
//   언제: C2 구현 시
export function SignupPage() {
  const { state } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const from = readFrom(location.state);

  // 가입·로그인 성공도 인증 상태가 바뀌어 여기서 한 번에 이동한다(auth-account.md D-5).
  if (state.status === 'authenticated') {
    return <Navigate replace to={resolvePostLoginPath(state.user, from)} />;
  }
  if (state.status === 'loading') return <div className="app" aria-busy="true" />;

  function onLoginFailed() {
    void navigate(ROUTES.login, {
      replace: true,
      state: { from: from ?? undefined, notice: 'signupLoginFailed' },
    });
  }

  return (
    <div className="app">
      <div className="bar">
        <Link to={ROUTES.login} state={location.state} aria-label={BACK_LABEL}>
          ←
        </Link>
        <h1 className="t">회원가입</h1>
        <span className="sp"></span>
      </div>
      <SignupForm initialRole={readSignupRole(location.search)} onLoginFailed={onLoginFailed} />
    </div>
  );
}
