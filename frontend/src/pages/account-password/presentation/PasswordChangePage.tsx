import { Link, useLocation } from 'react-router';
import {
  BACK_LABEL,
  PasswordChangeForm,
  readFrom,
  resolvePostLoginPath,
  useAuth,
} from '@/features/auth';

// C9. AccountLayout이 로그인을 보장한다. ← 규칙은 C8과 같다(auth-account.md D-4).
export function PasswordChangePage() {
  const { state } = useAuth();
  const location = useLocation();
  if (state.status !== 'authenticated') return null;
  const back = resolvePostLoginPath(state.user, readFrom(location.state));

  return (
    <div className="app">
      <div className="bar">
        <Link to={back} aria-label={BACK_LABEL}>
          ←
        </Link>
        <h1 className="t">비밀번호 변경</h1>
        <span className="sp" />
      </div>
      <PasswordChangeForm />
    </div>
  );
}
