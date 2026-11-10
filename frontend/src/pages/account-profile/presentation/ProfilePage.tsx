import { Link, useLocation } from 'react-router';
import { BACK_LABEL, ProfileForm, readFrom, resolvePostLoginPath, useAuth } from '@/features/auth';

// C8. AccountLayout이 로그인을 보장한다. ← 는 들어온 화면(from) 또는 역할별 도착지로 간다(auth-account.md D-4).
export function ProfilePage() {
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
        <h1 className="t">프로필 변경</h1>
        <span className="sp" />
      </div>
      <ProfileForm />
    </div>
  );
}
