import { useState } from 'react';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { LeaveCheckoutSheet } from '@/features/reservations';
import {
  LEAVE_CANCEL_LABEL,
  LEAVE_CONTINUE_LABEL,
  LEAVE_PAY_LATER_LABEL,
} from '@/features/reservations/domain/messages';
import { renderWithDeps } from '../../../support/renderWithDeps';

function renderSheet() {
  const handlers = { onContinue: vi.fn(), onCancelled: vi.fn(), onPayLater: vi.fn() };
  const { fakes } = renderWithDeps(<LeaveCheckoutSheet reservationId="r1" {...handlers} />);
  return { ...handlers, fakes };
}

describe('LeaveCheckoutSheet (C3a)', () => {
  it('「결제 계속하기」 → onContinue', async () => {
    const { onContinue, fakes } = renderSheet();
    await userEvent.click(screen.getByRole('button', { name: LEAVE_CONTINUE_LABEL }));
    expect(onContinue).toHaveBeenCalled();
    expect(fakes.reservations.cancel).not.toHaveBeenCalled();
  });

  it('「예약 취소하고 나가기」 → cancel(r1) 뒤 onCancelled', async () => {
    const { onCancelled, fakes } = renderSheet();
    await userEvent.click(screen.getByRole('button', { name: LEAVE_CANCEL_LABEL }));
    expect(fakes.reservations.cancel.mock.calls[0]?.[0]).toBe('r1');
    await waitFor(() => expect(onCancelled).toHaveBeenCalled());
  });

  it('「나중에 결제 (내 예약에 남음)」 → onPayLater, cancel 호출 없음', async () => {
    const { onPayLater, fakes } = renderSheet();
    await userEvent.click(screen.getByText(LEAVE_PAY_LATER_LABEL));
    expect(onPayLater).toHaveBeenCalled();
    expect(fakes.reservations.cancel).not.toHaveBeenCalled();
  });
});

it('C3a는 결제 계속하기에 초점을 두고 양방향 Tab을 가두며 닫으면 복귀한다', async () => {
  function Harness() {
    const [open, setOpen] = useState(false);
    return (
      <>
        <button type="button" onClick={() => setOpen(true)}>
          결제 이탈 시트 열기
        </button>
        {open ? (
          <LeaveCheckoutSheet
            reservationId="r1"
            onContinue={() => setOpen(false)}
            onCancelled={vi.fn()}
            onPayLater={vi.fn()}
          />
        ) : null}
      </>
    );
  }
  renderWithDeps(<Harness />);
  const trigger = screen.getByRole('button', { name: '결제 이탈 시트 열기' });
  await userEvent.click(trigger);
  const safe = screen.getByRole('button', { name: LEAVE_CONTINUE_LABEL });
  const last = screen.getByRole('button', { name: LEAVE_PAY_LATER_LABEL });
  await waitFor(() => expect(safe).toHaveFocus());
  await userEvent.tab({ shift: true });
  expect(last).toHaveFocus();
  await userEvent.tab();
  expect(safe).toHaveFocus();
  await userEvent.click(safe);
  await waitFor(() => expect(trigger).toHaveFocus());
});
