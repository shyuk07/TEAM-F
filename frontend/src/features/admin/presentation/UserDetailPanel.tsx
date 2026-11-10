import { useState } from 'react';
import { useUserDetail, useUserPoints } from '../application/useAdminQueries';
import type { AdminUserDetail } from '../domain/adminUser';
import {
  displayName,
  formatPoint,
  formatShortDate,
  formatSignedPoint,
  maskPhone,
  pointTypeLabel,
} from '../domain/labels';
import { availableUserActions } from '../domain/userActions';
import { AccountStatusTag } from './AccountStatusTag';
import { LoadError } from './LoadStates';
import { PointGrantSheet } from './PointGrantSheet';
import { SanctionSheet } from './SanctionSheet';

// 「최근 포인트 내역」 건수 (admin.md D-6)
const RECENT_POINTS = 5;

type Sheet = 'none' | 'grant' | 'suspend' | 'withdraw';

// TODO: 강제 탈퇴 결과 문구 「탈퇴 처리했어요 · 취소한 예약 N건」은 임시 문구다.
//   왜: screens.md M3·M2에 결과 문구가 없다 (docs/design/frontend/admin.md C-2, D-7)
//   언제: 결정 후 (디자인 시스템: content.md 관리자 결과 문구 확정)
export function UserDetailPanel({ userId, onChanged }: { userId: string; onChanged(): void }) {
  const detail = useUserDetail(userId);
  const points = useUserPoints(userId, RECENT_POINTS);
  const [sheet, setSheet] = useState<Sheet>('none');
  const [withdrawnCount, setWithdrawnCount] = useState<number | null>(null);

  const reloadAll = () => {
    detail.reload();
    points.reload();
    onChanged();
  };

  if (detail.status === 'loading') {
    return (
      <div className="box" aria-busy="true" aria-label="불러오는 중">
        <div className="sk" style={{ width: '40%' }} />
        <div className="sk" style={{ width: '70%' }} />
        <div className="sk" style={{ width: '55%' }} />
      </div>
    );
  }
  if (detail.status === 'error') {
    return (
      <div className="box">
        <LoadError error={detail.error} onRetry={detail.reload} />
      </div>
    );
  }

  const user: AdminUserDetail = detail.data;
  const name = displayName(user);
  const balance = points.status === 'success' ? points.data.balance : user.point;
  const actions = availableUserActions(user);
  const phone = maskPhone(user.phone);

  return (
    <div className="box" style={{ alignContent: 'start' }}>
      <div className="t">{name}</div>
      <div className="m">{phone === '' ? user.email : `${user.email} · ${phone}`}</div>
      <div className="kv">
        <span>상태</span>
        <AccountStatusTag status={user.status} />
      </div>
      <div className="kv">
        <span>포인트</span>
        <b>{formatPoint(balance)}</b>
      </div>
      <div className="lbl">최근 포인트 내역</div>
      {points.status === 'loading' ? <div className="sk" style={{ width: '60%' }} /> : null}
      {points.status === 'error' ? (
        <LoadError error={points.error} onRetry={points.reload} />
      ) : null}
      {points.status === 'success'
        ? points.data.entries.map((p, i) => (
            <div className="kv" key={p.id ?? `p-${i}`}>
              <span className="m">
                {p.createdAt !== null ? `${formatShortDate(p.createdAt)} ` : ''}
                {pointTypeLabel(p.type)} <span className="code-tag">{p.type}</span>
              </span>
              <span>{formatSignedPoint(p.amount)}</span>
            </div>
          ))
        : null}
      {withdrawnCount !== null ? (
        <div className="m" role="status">{`탈퇴 처리했어요 · 취소한 예약 ${withdrawnCount}건`}</div>
      ) : null}
      {actions.grantPoints || actions.suspend || actions.withdraw ? (
        <div className="row">
          {actions.grantPoints ? (
            <button type="button" className="btn sm" onClick={() => setSheet('grant')}>
              포인트 지급
            </button>
          ) : null}
          {actions.suspend ? (
            <button type="button" className="btn sm" onClick={() => setSheet('suspend')}>
              정지
            </button>
          ) : null}
          <span className="sp"></span>
          {actions.withdraw ? (
            <button
              type="button"
              className="link"
              style={{ background: 'none', border: 0, padding: 0, cursor: 'pointer' }}
              onClick={() => setSheet('withdraw')}
            >
              강제 탈퇴
            </button>
          ) : null}
        </div>
      ) : null}

      {sheet === 'grant' ? (
        <PointGrantSheet
          target={{ id: user.id, name, email: user.email, balance }}
          onClose={() => setSheet('none')}
          onDone={() => {
            setSheet('none');
            reloadAll();
          }}
        />
      ) : null}
      {sheet === 'suspend' || sheet === 'withdraw' ? (
        <SanctionSheet
          kind={sheet === 'suspend' ? 'suspendUser' : 'withdrawUser'}
          target={{ id: user.id, label: `${name} (${user.email})` }}
          facts={
            <div className="kv">
              <span>상태</span>
              <AccountStatusTag status={user.status} />
            </div>
          }
          onClose={() => setSheet('none')}
          onDone={(result) => {
            setSheet('none');
            if (result.kind === 'withdrawn') setWithdrawnCount(result.cancelledReservationCount);
            reloadAll();
          }}
        />
      ) : null}
    </div>
  );
}
