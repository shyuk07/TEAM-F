import { Link, Navigate, useLocation, useNavigate } from 'react-router';
import {
  BACK_LABEL,
  PasswordResetForm,
  readFrom,
  resolvePostLoginPath,
  useAuth,
} from '@/features/auth';
import { ROUTES } from '@/shared/lib/routes';

export function PasswordResetPage() {
  const { state } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const from = readFrom(location.state);

  if (state.status === 'authenticated') {
    return <Navigate replace to={resolvePostLoginPath(state.user, from)} />;
  }
  if (state.status === 'loading') return <div className="app" aria-busy="true" />;

  // 재설정 성공 뒤 A1에서 새 비밀번호로 로그인하게 한다(auth-account.md D-10).
  function onDone() {
    void navigate(ROUTES.login, {
      replace: true,
      state: { from: from ?? undefined, notice: 'passwordReset' },
    });
  }

  return (
    <div className="app">
      <div className="bar">
        <Link to={ROUTES.login} state={location.state} aria-label={BACK_LABEL}>
          ←
        </Link>
        <h1 className="t">비밀번호 재설정</h1>
        <span className="sp"></span>
      </div>
      <PasswordResetForm onDone={onDone} />
    </div>
  );
}
