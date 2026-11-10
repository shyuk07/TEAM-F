import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { ReservationCard } from '@/features/reservations/presentation/ReservationCard';
import type { Reservation } from '@/features/reservations';
import { PICKUP_CODE_LABEL, RESERVE_CONTINUE_LABEL } from '@/features/reservations/domain/messages';
import { at, makeReservation } from '../fakes/reservations';

function renderCard(reservation: Reservation, now: Date) {
  const onCancel = vi.fn();
  const onContinuePayment = vi.fn();
  render(
    <MemoryRouter>
      <ReservationCard
        reservation={reservation}
        now={now}
        onCancel={onCancel}
        onContinuePayment={onContinuePayment}
      />
    </MemoryRouter>,
  );
  return { onCancel, onContinuePayment };
}

describe('ReservationCard (C5·C5b)', () => {
  it('RESERVED 16:00: 픽업 코드·코드 라벨·「예약 취소 · 17:00까지」', () => {
    renderCard(makeReservation(), at(16));
    expect(screen.getByText('A12345')).toBeInTheDocument();
    expect(screen.getByText(PICKUP_CODE_LABEL)).toBeInTheDocument();
    expect(screen.getByText('예약 취소 · 17:00까지')).toBeInTheDocument();
  });

  it('「예약 취소」를 누르면 onCancel(예약)', async () => {
    const r = makeReservation();
    const { onCancel } = renderCard(r, at(16));
    await userEvent.click(screen.getByText('예약 취소 · 17:00까지'));
    expect(onCancel).toHaveBeenCalledWith(r);
  });

  it('취소 마감 정각 17:00에도 취소 링크가 있다', () => {
    renderCard(makeReservation(), at(17));
    expect(screen.getByText('예약 취소 · 17:00까지')).toBeInTheDocument();
  });

  it('17:00:01이면 「취소 마감 지남 (17:00)」 텍스트, 취소 링크 없음', () => {
    renderCard(makeReservation(), at(17, 0, 1));
    expect(screen.getByText('취소 마감 지남 (17:00)')).toBeInTheDocument();
    expect(screen.queryByText(/예약 취소/)).not.toBeInTheDocument();
  });

  it('PENDING이면 「결제 이어하기」 버튼이 onContinuePayment(id)', async () => {
    const { onContinuePayment } = renderCard(
      makeReservation({ status: 'PENDING_PAYMENT' }),
      at(16),
    );
    expect(screen.getByText('결제 대기')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: RESERVE_CONTINUE_LABEL }));
    expect(onContinuePayment).toHaveBeenCalledWith('r1');
  });

  it('STORE 취소면 「매장 사정으로 취소됨」 태그, 취소 링크·코드 없음', () => {
    renderCard(makeReservation({ status: 'CANCELLED', cancelledBy: 'STORE' }), at(16));
    expect(screen.getByText('매장 사정으로 취소됨')).toBeInTheDocument();
    expect(screen.queryByText(/예약 취소/)).not.toBeInTheDocument();
    expect(screen.queryByText('A12345')).not.toBeInTheDocument();
  });

  it('미수령(20:00:01)이면 「픽업 시간 지남」', () => {
    renderCard(makeReservation(), at(20, 0, 1));
    expect(screen.getByText('픽업 시간 지남')).toBeInTheDocument();
  });

  it('픽업 시간대 18:00–20:00과 「15:30 예약」을 보여 준다', () => {
    renderCard(makeReservation(), at(16));
    expect(screen.getByText(/18:00–20:00/)).toBeInTheDocument();
    expect(screen.getByText(/15:30 예약/)).toBeInTheDocument();
  });
});
