import { useId } from 'react';
import type { SignupRole } from '../domain/signupInput';

// 내부 부품(공개 API 아님): A2 역할 선택. 두 항목뿐이라 방향키 이동 없이 Tab·클릭으로 고른다(auth-account.md D-21).
export function SignupRolePicker({
  value,
  onChange,
}: {
  value: SignupRole;
  onChange(role: SignupRole): void;
}) {
  const labelId = useId();
  return (
    <>
      <div className="lbl" id={labelId}>
        어떻게 이용하시나요? *
      </div>
      <div className="pick" role="radiogroup" aria-labelledby={labelId}>
        <button
          type="button"
          role="radio"
          aria-checked={value === 'CUSTOMER'}
          className={value === 'CUSTOMER' ? 'pcard on' : 'pcard'}
          onClick={() => onChange('CUSTOMER')}
        >
          <span className="ic">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M6 8h12l-1 12H7L6 8z" />
              <path d="M9 8V6a3 3 0 0 1 6 0v2" />
            </svg>
          </span>
          <b>일반 고객</b>
          <span className="m">할인을 예약하고 픽업</span>
        </button>
        <button
          type="button"
          role="radio"
          aria-checked={value === 'OWNER'}
          className={value === 'OWNER' ? 'pcard on' : 'pcard'}
          onClick={() => onChange('OWNER')}
        >
          <span className="ic">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <path d="M4 10v10h16V10" />
              <path d="M3 10l2-6h14l2 6" />
              <path d="M3 10a3 3 0 0 0 6 0a3 3 0 0 0 6 0a3 3 0 0 0 6 0" />
              <path d="M10 20v-5h4v5" />
            </svg>
          </span>
          <b>상점주</b>
          <span className="m">할인을 올리고 픽업 관리</span>
        </button>
      </div>
    </>
  );
}
