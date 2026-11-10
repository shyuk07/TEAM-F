import { useId, useRef, useState, type FormEvent } from 'react';
import { useAuth } from '../application/authContext';
import { readErrorInfo } from '../application/errorInfo';
import { canSubmitLogin } from '../domain/loginInput';
import { loginErrorMessage } from '../domain/loginMessage';

// TODO: 임시 문구다(로그인 실패 기본 문구, 「다시 시도」, 「닫기」, 「계정 메뉴」). 정본 문구가 정해지면 바꾼다.
//   왜: screens.md·content.md에 해당 문구가 없다 (docs/design/frontend/auth.md D-9)
//   언제: 결정 후 (디자인 시스템: content.md 문구 확정)
export function LoginForm() {
  const { login } = useAuth();
  const emailId = useId();
  const passwordId = useId();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const submitting = useRef(false);

  const canSubmit = canSubmitLogin(email, password);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!canSubmit || submitting.current) return;
    submitting.current = true;
    setPending(true);
    setError(null);
    try {
      await login(email, password);
      // 성공하면 LoginPage가 이동시키므로 여기서는 아무것도 하지 않는다.
    } catch (err) {
      setError(loginErrorMessage(readErrorInfo(err)));
      setPending(false);
      submitting.current = false;
    }
  }

  return (
    <form
      noValidate
      onSubmit={(e) => void onSubmit(e)}
      style={{ display: 'grid', gap: 'var(--s2)' }}
    >
      <label className="lbl" htmlFor={emailId}>
        이메일
      </label>
      <input
        id={emailId}
        className="in"
        type="email"
        autoComplete="username"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <label className="lbl" htmlFor={passwordId}>
        비밀번호
      </label>
      <input
        id={passwordId}
        className="in"
        type="password"
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      {error !== null ? (
        <div className="err" role="alert">
          {error}
        </div>
      ) : null}
      <button
        type="submit"
        className="btn pri"
        aria-disabled={!canSubmit || pending ? 'true' : undefined}
      >
        {pending ? '처리 중…' : '로그인'}
      </button>
    </form>
  );
}
