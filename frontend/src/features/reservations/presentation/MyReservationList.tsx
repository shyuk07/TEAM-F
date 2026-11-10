import { Link } from 'react-router';
import { ROUTES } from '@/shared/lib/routes';
import { useMyReservations } from '../application/useMyReservations';
import { useNow } from '../application/useNow';
import type { ReservationTab } from '../domain/grouping';
import {
  EMPTY_ACTION_LABEL,
  EMPTY_ACTIVE_MESSAGE,
  EMPTY_PAST_MESSAGE,
  ERROR_FALLBACK_MESSAGE,
  RETRY_LABEL,
  TAB_ACTIVE_LABEL,
  TAB_PAST_LABEL,
} from '../domain/messages';
import type { Reservation } from '../domain/reservation';
import { ReservationCard } from './ReservationCard';

export type MyReservationListProps = {
  tab: ReservationTab;
  onTabChange(tab: ReservationTab): void;
  onCancel(reservation: Reservation): void;
  onContinuePayment(reservationId: string): void;
};

const SKELETON_COUNT = 3;

export function MyReservationList({
  tab,
  onTabChange,
  onCancel,
  onContinuePayment,
}: MyReservationListProps) {
  const state = useMyReservations();
  const now = useNow();

  const chips = (
    <div className="scroll">
      {(
        [
          ['active', TAB_ACTIVE_LABEL],
          ['past', TAB_PAST_LABEL],
        ] as const
      ).map(([key, label]) => (
        <button
          key={key}
          type="button"
          className={tab === key ? 'chip on' : 'chip'}
          aria-pressed={tab === key}
          onClick={() => onTabChange(key)}
        >
          {label}
        </button>
      ))}
    </div>
  );

  let content;
  if (state.status === 'loading') {
    content = (
      <div aria-busy="true">
        {Array.from({ length: SKELETON_COUNT }, (_, i) => (
          <div key={i} className="card">
            <div className="sk"></div>
            <div className="sk"></div>
          </div>
        ))}
      </div>
    );
  } else if (state.status === 'error') {
    content = (
      <>
        <div className="err" role="alert">
          {state.message !== '' ? state.message : ERROR_FALLBACK_MESSAGE}
        </div>
        <button type="button" className="btn" onClick={state.reload}>
          {RETRY_LABEL}
        </button>
      </>
    );
  } else {
    const list = tab === 'active' ? state.active : state.past;
    content =
      list.length === 0 ? (
        <div className="box empty">
          <b>{tab === 'active' ? EMPTY_ACTIVE_MESSAGE : EMPTY_PAST_MESSAGE}</b>
          <Link className="btn sm" to={ROUTES.home}>
            {EMPTY_ACTION_LABEL}
          </Link>
        </div>
      ) : (
        <div className="list">
          {list.map((r) => (
            <ReservationCard
              key={r.id}
              reservation={r}
              now={now}
              onCancel={onCancel}
              onContinuePayment={onContinuePayment}
            />
          ))}
        </div>
      );
  }

  return (
    <div className="body">
      {chips}
      {content}
    </div>
  );
}
