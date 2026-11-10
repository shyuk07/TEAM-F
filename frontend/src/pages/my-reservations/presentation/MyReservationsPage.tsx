import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router';
import {
  CancelReservationSheet,
  MyReservationList,
  type Reservation,
} from '@/features/reservations';
import { ROUTES } from '@/shared/lib/routes';

type Tab = 'active' | 'past';

// TODO: 고객 TabBar가 없다.
//   왜: 고객 셸이 설계되지 않았다 (docs/design/frontend/reservations.md C-5)
//   언제: 결정 후 (사용자: 고객 셸 설계)
export function MyReservationsPage() {
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const tab: Tab = params.get('tab') === 'past' ? 'past' : 'active';
  const [cancelling, setCancelling] = useState<Reservation | null>(null);
  const [listKey, setListKey] = useState(0);

  return (
    <>
      <div aria-hidden={cancelling !== null ? true : undefined}>
        <div className="bar">
          <h1 className="t">내 예약</h1>
          <span className="sp"></span>
        </div>
        <MyReservationList
          key={listKey}
          tab={tab}
          onTabChange={(next) => setParams(next === 'past' ? { tab: 'past' } : {})}
          onCancel={setCancelling}
          onContinuePayment={(id) => void navigate(ROUTES.checkout(id))}
        />
      </div>
      {cancelling !== null ? (
        <CancelReservationSheet
          reservation={cancelling}
          onClose={() => setCancelling(null)}
          onRefresh={() => setListKey((k) => k + 1)}
          onCancelled={() => {
            setCancelling(null);
            setListKey((k) => k + 1);
          }}
        />
      ) : null}
    </>
  );
}
