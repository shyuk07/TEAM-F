import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PaymentForm, type Payment } from '@/features/payments';
import { ApiError } from '@/shared/api/error';
import { createFakes, renderWithDeps, type DepsFakes } from '../../../support/renderWithDeps';
import { deferred } from '../../auth/fakes/deferred';

function isDisabled(el: HTMLElement): boolean {
  return (el as HTMLButtonElement).disabled || el.getAttribute('aria-disabled') === 'true';
}

function renderForm(fakes: DepsFakes = createFakes()) {
  const onPaid = vi.fn();
  renderWithDeps(
    <PaymentForm
      reservationId="r1"
      productName="식빵 모둠"
      quantity={2}
      totalPrice={11500}
      pointBalance={1240}
      onPaid={onPaid}
    />,
    { fakes },
  );
  return { onPaid, fakes };
}

const pointInput = () => screen.getByLabelText('포인트 사용 (100P 단위)');
const payButton = () => screen.getByRole('button', { name: /결제하기/ });

describe('PaymentForm (C3)', () => {
  it('초기 버튼 「결제하기 11,500원」, 적립 「결제 후 115P 적립 (1%)」', () => {
    renderForm();
    expect(screen.getByRole('button', { name: '결제하기 11,500원' })).toBeInTheDocument();
    expect(screen.getByText('결제 후 115P 적립 (1%)')).toBeInTheDocument();
  });

  it('「전액」을 누르면 입력이 1200, 버튼 「결제하기 10,300원」', async () => {
    renderForm();
    await userEvent.click(screen.getByRole('button', { name: '전액' }));
    expect(pointInput()).toHaveValue('1200');
    expect(screen.getByRole('button', { name: '결제하기 10,300원' })).toBeInTheDocument();
  });

  it('550을 입력하면 결제 버튼이 비활성(문구 단언은 D-5 확정 뒤)', async () => {
    renderForm();
    await userEvent.type(pointInput(), '550');
    expect(isDisabled(payButton())).toBe(true);
  });

  it('클릭하면 pay({reservationId, usePoint})를 부르고 처리 중 「처리 중…」 비활성', async () => {
    const fakes = createFakes();
    fakes.payments.pay.mockReturnValue(deferred<Payment>().promise);
    renderForm(fakes);
    await userEvent.type(pointInput(), '500');
    await userEvent.click(payButton());
    expect(fakes.payments.pay.mock.calls[0]?.[0]).toEqual({ reservationId: 'r1', usePoint: 500 });
    expect(isDisabled(await screen.findByRole('button', { name: '처리 중…' }))).toBe(true);
  });

  it('성공하면 onPaid(Payment)', async () => {
    const { onPaid } = renderForm();
    await userEvent.click(payButton());
    await waitFor(() => expect(onPaid).toHaveBeenCalledWith(expect.objectContaining({ id: 'p1' })));
  });

  it('서버 오류면 message를 보여 주고 버튼이 다시 활성', async () => {
    const fakes = createFakes();
    fakes.payments.pay.mockRejectedValue(new ApiError(409, 'CONFLICT', '이미 결제된 예약'));
    const { onPaid } = renderForm(fakes);
    await userEvent.click(payButton());
    expect(await screen.findByText('이미 결제된 예약')).toBeInTheDocument();
    expect(isDisabled(payButton())).toBe(false);
    expect(onPaid).not.toHaveBeenCalled();
  });
});
