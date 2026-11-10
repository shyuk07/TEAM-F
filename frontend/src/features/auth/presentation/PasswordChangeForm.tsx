import { useId, useState, type FormEvent } from 'react';
import { useChangePassword } from '../application/useChangePassword';
import {
  PASSWORD_CHANGED_NOTICE,
  PASSWORD_CONFIRM_MISMATCH_MESSAGE,
  changePasswordErrorView,
  passwordRuleMessage,
} from '../domain/accountMessages';
import {
  canSubmitPasswordChange,
  isConfirmMismatch,
  type PasswordChangeForm as PasswordChangeFormValue,
} from '../domain/passwordChange';
import { checkPassword } from '../domain/passwordRule';

const EMPTY_FORM: PasswordChangeFormValue = { current: '', next: '', confirm: '' };

// C9 비밀번호 변경. 성공하면 세 칸을 비우고 완료 문구를 보인다. 세션은 그대로다(auth-account.md D-9, D-12).
export function PasswordChangeForm() {
  const { submit, pending, error, done, reset } = useChangePassword();
  const [form, setForm] = useState<PasswordChangeFormValue>(EMPTY_FORM);
  const currentId = useId();
  const nextId = useId();
  const confirmId = useId();

  const ruleMessage = passwordRuleMessage(checkPassword(form.next));
  const mismatch = isConfirmMismatch(form.next, form.confirm);
  const errorView = error !== null ? changePasswordErrorView(error) : null;
  const disabled = !canSubmitPasswordChange(form) || pending;
  const label = pending ? '처리 중…' : '비밀번호 바꾸기';

  function change(next: Partial<PasswordChangeFormValue>) {
    setForm((prev) => ({ ...prev, ...next }));
    // 완료 표시·오류는 다음 입력에서 지운다.
    if (done || error !== null) reset();
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (disabled) return;
    if (await submit(form)) setForm(EMPTY_FORM);
  }

  return (
    <form noValidate onSubmit={(e) => void onSubmit(e)} style={{ display: 'contents' }}>
      <div className="body">
        <label className="lbl" htmlFor={currentId}>
          현재 비밀번호
        </label>
        <input
          id={currentId}
          className="in"
          type="password"
          autoComplete="current-password"
          value={form.current}
          onChange={(e) => change({ current: e.target.value })}
        />
        {errorView?.field === 'current' ? (
          <div className="err" role="alert">
            {errorView.message}
          </div>
        ) : null}
        <label className="lbl" htmlFor={nextId}>
          새 비밀번호 (8자 이상)
        </label>
        <input
          id={nextId}
          className="in"
          type="password"
          autoComplete="new-password"
          value={form.next}
          onChange={(e) => change({ next: e.target.value })}
        />
        {ruleMessage !== null ? (
          <div className="err" role="alert">
            {ruleMessage}
          </div>
        ) : null}
        <label className="lbl" htmlFor={confirmId}>
          새 비밀번호 확인
        </label>
        <input
          id={confirmId}
          className="in"
          type="password"
          autoComplete="new-password"
          value={form.confirm}
          onChange={(e) => change({ confirm: e.target.value })}
        />
        {mismatch ? (
          <div className="err" role="alert">
            {PASSWORD_CONFIRM_MISMATCH_MESSAGE}
          </div>
        ) : null}
        <div className="m">바꿔도 이 기기는 로그인이 유지되고, 다른 기기에서는 로그아웃돼요.</div>
        {done ? (
          <div className="box done" role="status">
            {PASSWORD_CHANGED_NOTICE}
          </div>
        ) : null}
        {errorView?.field === 'form' ? (
          <div className="err" role="alert">
            {errorView.message}
          </div>
        ) : null}
        <button type="submit" className="btn pri dk" aria-disabled={disabled ? 'true' : undefined}>
          {label}
        </button>
      </div>
      <div className="cta">
        <button type="submit" className="btn pri" aria-disabled={disabled ? 'true' : undefined}>
          {label}
        </button>
      </div>
    </form>
  );
}
