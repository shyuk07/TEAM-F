import { useId, useState, type FormEvent } from 'react';
import { useAuth } from '../application/authContext';
import { useUpdateProfile } from '../application/useUpdateProfile';
import { PROFILE_SAVED_NOTICE, accountErrorMessage } from '../domain/accountMessages';
import {
  canSaveProfile,
  isNameLocked,
  profileFormOf,
  profilePatch,
  type ProfileForm as ProfileFormValue,
} from '../domain/profileInput';
import { PROFILE_TEXT_MAX_LENGTH } from '../domain/signupInput';

const EMPTY_FORM: ProfileFormValue = { name: '', phone: '' };

// C8 프로필 변경. AccountLayout 안에서만 렌더한다(인증된 사용자 보장).
// 폼은 display: contents로 .body와 .cta를 감싸 .app의 flex 배치를 깨지 않는다(auth-account.md D-19).
// open-issues: C8 상점주 상호 칸 잠금, 전화번호만 수정
// TODO: 저장 뒤 「저장했어요」를 같은 화면에 표시하고 이전 화면으로 돌아가지 않는다.
//   왜: 디자인 시스템에 알림(토스트) 컴포넌트가 없어 이전 화면에 알림을 띄울 수 없다 (auth-account.md C-4, D-11)
//   언제: 결정 후 (디자인 시스템: 알림 컴포넌트)
export function ProfileForm() {
  const { state: auth } = useAuth();
  const user = auth.status === 'authenticated' ? auth.user : null;
  const { submit, pending, error, done, reset } = useUpdateProfile();
  const [form, setForm] = useState<ProfileFormValue>(() =>
    user !== null ? profileFormOf(user) : EMPTY_FORM,
  );
  const emailId = useId();
  const nameId = useId();
  const phoneId = useId();

  if (user === null) return null;

  const canSave = canSaveProfile(user, form);
  const disabled = !canSave || pending;
  const label = pending ? '처리 중…' : '저장';

  function change(next: Partial<ProfileFormValue>) {
    setForm((prev) => ({ ...prev, ...next }));
    // 완료 표시·오류는 다음 입력에서 지운다.
    if (done || error !== null) reset();
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (user === null || disabled) return;
    await submit(profilePatch(user, form));
  }

  return (
    <form noValidate onSubmit={(e) => void onSubmit(e)} style={{ display: 'contents' }}>
      <div className="body">
        <label className="lbl" htmlFor={emailId}>
          이메일 (변경 불가)
        </label>
        <input id={emailId} className="in ro" type="email" readOnly value={user.email} />
        {isNameLocked(user) ? (
          <>
            <label className="lbl" htmlFor={nameId}>
              상호 (변경 불가)
            </label>
            <input id={nameId} className="in ro" readOnly value={user.name ?? ''} />
          </>
        ) : (
          <>
            <label className="lbl" htmlFor={nameId}>
              이름
            </label>
            <input
              id={nameId}
              className="in"
              autoComplete="name"
              maxLength={PROFILE_TEXT_MAX_LENGTH}
              value={form.name}
              onChange={(e) => change({ name: e.target.value })}
            />
          </>
        )}
        <label className="lbl" htmlFor={phoneId}>
          전화번호
        </label>
        <input
          id={phoneId}
          className="in"
          type="tel"
          autoComplete="tel"
          maxLength={PROFILE_TEXT_MAX_LENGTH}
          value={form.phone}
          onChange={(e) => change({ phone: e.target.value })}
        />
        {done ? (
          <div className="box done" role="status">
            {PROFILE_SAVED_NOTICE}
          </div>
        ) : null}
        {error !== null ? (
          <div className="err" role="alert">
            {accountErrorMessage(error)}
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
