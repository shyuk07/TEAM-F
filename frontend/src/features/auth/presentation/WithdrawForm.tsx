import { useId, useState, type FormEvent } from 'react';
import { Link } from 'react-router';
import { useWithdraw } from '../application/useWithdraw';
import { WITHDRAW_RESERVATIONS_TEXT, withdrawErrorView } from '../domain/accountMessages';
import { pointExpiryText } from '../domain/points';

// C7 회원 탈퇴 확인. 성공하면 인증 상태가 anonymous(loggedOut)가 되어 고객 가드가 C1로 보낸다(customer-home.md D-24).
// 고객 셸은 420px라 .dk 버튼 두 벌을 두지 않는다(customer-home.md D-5).
// TODO: 진행 중 예약 줄에 건수 대신 「모두 취소·환불」을 보인다.
//   왜: 예약 건수는 reservations 영역 API가 필요하다 (customer-home.md C-6)
//   언제: C5 구현 시
export function WithdrawForm({ balance, cancelTo }: { balance: number; cancelTo: string }) {
  const { submit, pending, error } = useWithdraw();
  const [password, setPassword] = useState('');
  const passwordId = useId();

  const errorView = error !== null ? withdrawErrorView(error) : null;
  const disabled = password === '' || pending;

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (disabled) return;
    await submit(password);
  }

  return (
    <form noValidate onSubmit={(e) => void onSubmit(e)} style={{ display: 'contents' }}>
      <div className="body">
        <div className="box">
          <div className="t">탈퇴하면 이렇게 돼요</div>
          <div className="kv">
            <span>진행 중 예약</span>
            <b>{WITHDRAW_RESERVATIONS_TEXT}</b>
          </div>
          <div className="kv">
            <span>남은 포인트</span>
            <b className="cd">{pointExpiryText(balance)}</b>
          </div>
          <div className="m">되돌릴 수 없어요.</div>
        </div>
        <label className="lbl" htmlFor={passwordId}>
          현재 비밀번호 *
        </label>
        <input
          id={passwordId}
          className="in"
          type="password"
          autoComplete="current-password"
          maxLength={128}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {errorView?.field === 'password' ? (
          <div className="err" role="alert">
            {errorView.message}
          </div>
        ) : null}
        {errorView?.field === 'form' ? (
          <div className="err" role="alert">
            {errorView.message}
          </div>
        ) : null}
      </div>
      <div className="cta">
        <Link className="btn" to={cancelTo}>
          취소
        </Link>
        <button type="submit" className="btn dark" aria-disabled={disabled ? 'true' : undefined}>
          {pending ? '처리 중…' : '탈퇴하기'}
        </button>
      </div>
    </form>
  );
}
