import { useState } from 'react';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CancelReservationSheet } from '@/features/reservations';
import {
  CANCEL_SHEET_BACK_LABEL,
  CANCEL_SHEET_CONFIRM_LABEL,
  PROCESSING_LABEL,
  REFUND_NOTICE,
} from '@/features/reservations/domain/messages';
import { ApiError } from '@/shared/api/error';
import { createFakes, renderWithDeps, type DepsFakes } from '../../../support/renderWithDeps';
import { deferred } from '../../auth/fakes/deferred';
import { makeReservation } from '../fakes/reservations';

type CancelResult = Awaited<ReturnType<DepsFakes['reservations']['cancel']>>;

function isDisabled(el: HTMLElement): boolean {
  return (el as HTMLButtonElement).disabled || el.getAttribute('aria-disabled') === 'true';
}

function renderSheet(fakes: DepsFakes = createFakes()) {
  const onClose = vi.fn();
  const onCancelled = vi.fn();
  renderWithDeps(
    <CancelReservationSheet
      reservation={makeReservation()}
      onClose={onClose}
      onCancelled={onCancelled}
    />,
    { fakes },
  );
  return { onClose, onCancelled, fakes };
}

describe('CancelReservationSheet (C5a)', () => {
  it('「돌아가기」 → onClose, cancel 호출 없음', async () => {
    const { onClose, fakes } = renderSheet();
    await userEvent.click(screen.getByRole('button', { name: CANCEL_SHEET_BACK_LABEL }));
    expect(onClose).toHaveBeenCalled();
    expect(fakes.reservations.cancel).not.toHaveBeenCalled();
  });

  it('환불 안내가 있다(문구는 D-14 임시 상수)', () => {
    renderSheet();
    expect(screen.getByText(REFUND_NOTICE)).toBeInTheDocument();
  });

  it('「예약 취소」 → cancel(id), 성공하면 onCancelled', async () => {
    const { onCancelled, fakes } = renderSheet();
    await userEvent.click(screen.getByRole('button', { name: CANCEL_SHEET_CONFIRM_LABEL }));
    expect(fakes.reservations.cancel.mock.calls[0]?.[0]).toBe('r1');
    await waitFor(() => expect(onCancelled).toHaveBeenCalled());
  });

  it('처리 중에는 「처리 중…」 비활성', async () => {
    const fakes = createFakes();
    fakes.reservations.cancel.mockReturnValue(deferred<CancelResult>().promise);
    renderSheet(fakes);
    await userEvent.click(screen.getByRole('button', { name: CANCEL_SHEET_CONFIRM_LABEL }));
    expect(isDisabled(await screen.findByRole('button', { name: PROCESSING_LABEL }))).toBe(true);
  });

  it('400 CANCELLATION_DEADLINE_PASSED면 서버 message를 보여 주고 onCancelled는 부르지 않는다', async () => {
    const fakes = createFakes();
    fakes.reservations.cancel.mockRejectedValue(
      new ApiError(400, 'CANCELLATION_DEADLINE_PASSED', '취소 가능 시각이 지났습니다.'),
    );
    const { onCancelled } = renderSheet(fakes);
    await userEvent.click(screen.getByRole('button', { name: CANCEL_SHEET_CONFIRM_LABEL }));
    expect(await screen.findByText('취소 가능 시각이 지났습니다.')).toBeInTheDocument();
    expect(onCancelled).not.toHaveBeenCalled();
    expect(isDisabled(screen.getByRole('button', { name: CANCEL_SHEET_CONFIRM_LABEL }))).toBe(
      false,
    );
  });
});

describe('C5a 리뷰 회귀', () => {
  it('결제 내역이 없는 예약 총액을 현금 환불액으로 표시하지 않는다', () => {
    renderSheet();
    expect(screen.queryByText('돌려받는 금액')).not.toBeInTheDocument();
    expect(screen.queryByText('11,500원')).not.toBeInTheDocument();
    expect(screen.getByText(REFUND_NOTICE)).toBeInTheDocument();
  });

  it('안전한 돌아가기에 초점을 두고 Tab을 가두며 닫으면 원래 버튼으로 복귀한다', async () => {
    function Harness() {
      const [open, setOpen] = useState(false);
      return (
        <>
          <button type="button" onClick={() => setOpen(true)}>
            취소 시트 열기
          </button>
          {open ? (
            <CancelReservationSheet
              reservation={makeReservation()}
              onClose={() => setOpen(false)}
              onCancelled={vi.fn()}
            />
          ) : null}
        </>
      );
    }
    renderWithDeps(<Harness />);
    const trigger = screen.getByRole('button', { name: '취소 시트 열기' });
    await userEvent.click(trigger);
    const back = screen.getByRole('button', { name: CANCEL_SHEET_BACK_LABEL });
    const confirm = screen.getByRole('button', { name: CANCEL_SHEET_CONFIRM_LABEL });
    await waitFor(() => expect(back).toHaveFocus());
    await userEvent.tab({ shift: true });
    expect(confirm).toHaveFocus();
    await userEvent.tab();
    expect(back).toHaveFocus();
    await userEvent.click(back);
    await waitFor(() => expect(trigger).toHaveFocus());
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
  });
});
