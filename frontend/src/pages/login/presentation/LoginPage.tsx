import { Link, Navigate, useLocation } from 'react-router';
import {
  LoginForm,
  loginEntryMessage,
  loginNoticeMessage,
  readFrom,
  readLoginEntry,
  readLoginNotice,
  resolvePostLoginPath,
  useAuth,
} from '@/features/auth';
import { ROUTES } from '@/shared/lib/routes';

export function LoginPage() {
  const { state } = useAuth();
  const location = useLocation();
  const from = readFrom(location.state);

  if (state.status === 'authenticated') {
    return <Navigate replace to={resolvePostLoginPath(state.user, from)} />;
  }
  if (state.status === 'loading') return <div className="app" aria-busy="true" />;

  // A2·A3로 갈 때 from을 넘겨 가입·재설정 뒤에도 원래 화면으로 돌아오게 한다(auth-account.md D-7).
  const linkState = from !== null ? { from } : undefined;
  const notice = readLoginNotice(location.state);
  // 진입 경로별 안내 한 줄(wireframe.html:170). 고객 가드는 customerTab, C2는 reservation(customer-home.md §3.7, §5.6)
  const entry = readLoginEntry(location.state);

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
        {entry !== null ? <div className="m">{loginEntryMessage(entry)}</div> : null}
        {notice !== null ? (
          <div className="box done" role="status">
            {loginNoticeMessage(notice)}
          </div>
        ) : null}
        <LoginForm />
        <Link className="link" to={ROUTES.passwordReset} state={linkState}>
          비밀번호 재설정
        </Link>
      </div>
      {/* .cta는 720px 이상에서 숨는다(bundle.css). 가입 링크는 PC에서도 보여야 하므로 display를 직접 지정한다 */}
      <div
        className="cta"
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'stretch',
          gap: 'var(--s2)',
        }}
      >
        <span className="m" style={{ textAlign: 'center' }}>
          계정이 없나요?
        </span>
        <Link className="btn" to={ROUTES.signup} state={linkState}>
          회원가입
        </Link>
        <Link className="link" to={ROUTES.ownerSignup} state={linkState}>
          사장님이신가요? 입점 신청
        </Link>
      </div>
    </div>
  );
}
