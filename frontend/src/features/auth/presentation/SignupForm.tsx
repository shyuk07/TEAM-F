import { useId, useState, type FormEvent } from 'react';
import { useSignup } from '../application/useSignup';
import { passwordRuleMessage, signupErrorView } from '../domain/accountMessages';
import { checkPassword } from '../domain/passwordRule';
import {
  EMAIL_MAX_LENGTH,
  PROFILE_TEXT_MAX_LENGTH,
  canSubmitSignup,
  nameLabel,
  type SignupForm as SignupFormValues,
  type SignupRole,
} from '../domain/signupInput';
import { SignupRolePicker } from './SignupRolePicker';

// A2 폼 전체(본문 칸 + 주 버튼 .dk·.cta 두 벌). 이동은 page가 한다: 로그인 성공은 인증 상태 변화로, 로그인 실패는 onLoginFailed로.
export function SignupForm({
  initialRole,
  onLoginFailed,
}: {
  initialRole: SignupRole;
  onLoginFailed(): void;
}) {
  const nameId = useId();
  const emailId = useId();
  const passwordId = useId();
  const phoneId = useId();
  const [form, setForm] = useState<SignupFormValues>({
    role: initialRole,
    name: '',
    email: '',
    password: '',
    phone: '',
  });
  const { submit, pending, error } = useSignup();

  const canSubmit = canSubmitSignup(form);
  const disabled = !canSubmit || pending;
  const ruleMessage = passwordRuleMessage(checkPassword(form.password));
  const errorView = error !== null ? signupErrorView(error) : null;

  function update<K extends keyof SignupFormValues>(key: K, value: SignupFormValues[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (disabled) return;
    const outcome = await submit(form);
    if (outcome?.kind === 'loginFailed') onLoginFailed();
  }

  const submitLabel = pending ? '처리 중…' : '가입하기';

  return (
    <form noValidate onSubmit={(e) => void onSubmit(e)} style={{ display: 'contents' }}>
      <div className="body">
        <SignupRolePicker value={form.role} onChange={(role) => update('role', role)} />
        <div className="m">
          한 계정은 한 가지 유형이에요. 상점주는 관리자 승인 후 상점을 열 수 있어요.
        </div>
        <label className="lbl" htmlFor={nameId}>
          {nameLabel(form.role)}
        </label>
        <input
          id={nameId}
          className="in"
          autoComplete={form.role === 'OWNER' ? 'organization' : 'name'}
          maxLength={PROFILE_TEXT_MAX_LENGTH}
          value={form.name}
          onChange={(e) => update('name', e.target.value)}
        />
        <label className="lbl" htmlFor={emailId}>
          이메일 *
        </label>
        <input
          id={emailId}
          className="in"
          type="email"
          autoComplete="username"
          maxLength={EMAIL_MAX_LENGTH}
          value={form.email}
          onChange={(e) => update('email', e.target.value)}
        />
        {errorView?.field === 'email' ? (
          <div className="err" role="alert">
            {errorView.message}
          </div>
        ) : null}
        <label className="lbl" htmlFor={passwordId}>
          비밀번호 * (8자 이상)
        </label>
        <input
          id={passwordId}
          className="in"
          type="password"
          autoComplete="new-password"
          value={form.password}
          onChange={(e) => update('password', e.target.value)}
        />
        {ruleMessage !== null ? (
          <div className="err" role="alert">
            {ruleMessage}
          </div>
        ) : null}
        <label className="lbl" htmlFor={phoneId}>
          전화번호 *
        </label>
        <input
          id={phoneId}
          className="in"
          type="tel"
          autoComplete="tel"
          maxLength={PROFILE_TEXT_MAX_LENGTH}
          value={form.phone}
          onChange={(e) => update('phone', e.target.value)}
        />
        {errorView?.field === 'form' ? (
          <div className="err" role="alert">
            {errorView.message}
          </div>
        ) : null}
        <button type="submit" className="btn pri dk" aria-disabled={disabled ? 'true' : undefined}>
          {submitLabel}
        </button>
      </div>
      <div className="cta">
        <button type="submit" className="btn pri" aria-disabled={disabled ? 'true' : undefined}>
          {submitLabel}
        </button>
      </div>
    </form>
  );
}
