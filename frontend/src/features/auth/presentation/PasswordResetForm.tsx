import { useId, useState, type FormEvent } from 'react';
import { usePasswordReset } from '../application/usePasswordReset';
import {
  accountErrorMessage,
  passwordRuleMessage,
  resetConfirmErrorMessage,
} from '../domain/accountMessages';
import { canConfirmReset, canRequestReset } from '../domain/passwordReset';
import { checkPassword } from '../domain/passwordRule';
import { EMAIL_MAX_LENGTH } from '../domain/signupInput';

// open-issues: A3 메일 발송 확인 필요 (화면은 가입 여부와 무관하게 같은 안내만 보임)
export function PasswordResetForm({ onDone }: { onDone(): void }) {
  const emailId = useId();
  const codeId = useId();
  const passwordId = useId();
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const reset = usePasswordReset();

  const codeSent = reset.sentEmail !== null;
  const requestDisabled = !canRequestReset(email) || reset.requestPending;
  const confirmDisabled = !canConfirmReset({ codeSent, code, newPassword }) || reset.confirmPending;
  const ruleMessage = passwordRuleMessage(checkPassword(newPassword));

  // 코드를 보낸 뒤 이메일을 고치면 2단계를 닫고 코드를 비운다(다른 이메일의 코드로 확인하는 실수 방지, auth-account.md D-24).
  // 요청 대기 중에는 이메일 칸이 readOnly라 여기로 오지 않는다(늦게 온 204가 다른 이메일로 2단계를 여는 것 방지, D-24).
  function onEmailChange(value: string) {
    setEmail(value);
    if (codeSent) {
      reset.invalidate();
      setCode('');
    }
  }

  function onRequest() {
    if (requestDisabled) return;
    void reset.request(email);
  }

  // TODO: 60초 안에 다시 받으면 서버가 새 코드를 만들지 않는데 화면은 알려 주지 않는다.
  //   왜: 재요청 간격 안내 문구가 정본에 없다 (reference/auth.md §10, auth-account.md D-24)
  //   언제: 결정 후 (사용자: 재요청 간격 안내)
  function onResend() {
    if (reset.requestPending) return;
    void reset.resend();
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (confirmDisabled) return;
    if (await reset.confirm(code, newPassword)) onDone();
  }

  const confirmLabel = reset.confirmPending ? '처리 중…' : '비밀번호 바꾸기';

  return (
    <form noValidate onSubmit={(e) => void onSubmit(e)} style={{ display: 'contents' }}>
      <div className="body">
        <div className="lbl">1단계 · 코드 받기</div>
        <div className="box">
          <label className="lbl" htmlFor={emailId}>
            가입한 이메일
          </label>
          <input
            id={emailId}
            className="in"
            type="email"
            autoComplete="username"
            maxLength={EMAIL_MAX_LENGTH}
            readOnly={reset.requestPending}
            value={email}
            onChange={(e) => onEmailChange(e.target.value)}
          />
          <button
            type="button"
            className="btn"
            aria-disabled={requestDisabled ? 'true' : undefined}
            onClick={onRequest}
          >
            {reset.requestPending ? '처리 중…' : '코드 보내기'}
          </button>
          <div className="m">가입된 이메일이면 6자리 코드를 보내요.</div>
          {reset.requestError !== null ? (
            <div className="err" role="alert">
              {accountErrorMessage(reset.requestError)}
            </div>
          ) : null}
        </div>
        {codeSent ? (
          <>
            <div className="lbl">2단계 · 새 비밀번호</div>
            <div className="box">
              <label className="lbl" htmlFor={codeId}>
                6자리 코드
              </label>
              <input
                id={codeId}
                className="in code"
                inputMode="numeric"
                autoComplete="one-time-code"
                maxLength={6}
                value={code}
                onChange={(e) => setCode(e.target.value)}
              />
              <label className="lbl" htmlFor={passwordId}>
                새 비밀번호 (8자 이상)
              </label>
              <input
                id={passwordId}
                className="in"
                type="password"
                autoComplete="new-password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
              />
              {ruleMessage !== null ? (
                <div className="err" role="alert">
                  {ruleMessage}
                </div>
              ) : null}
              {reset.confirmError !== null ? (
                <div className="err" role="alert">
                  {resetConfirmErrorMessage(reset.confirmError)}
                </div>
              ) : null}
              <button
                type="button"
                className="link"
                style={{ textAlign: 'left' }}
                onClick={onResend}
              >
                코드 다시 받기
              </button>
            </div>
          </>
        ) : null}
        <button
          type="submit"
          className="btn pri dk"
          aria-disabled={confirmDisabled ? 'true' : undefined}
        >
          {confirmLabel}
        </button>
      </div>
      <div className="cta">
        <button
          type="submit"
          className="btn pri"
          aria-disabled={confirmDisabled ? 'true' : undefined}
        >
          {confirmLabel}
        </button>
      </div>
    </form>
  );
}
