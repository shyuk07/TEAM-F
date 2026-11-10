import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PaymentForm } from '@/features/payments';
import { POINT_NOT_UNIT_MESSAGE } from '@/features/payments/domain/messages';
import { renderWithDeps } from '../../../support/renderWithDeps';

// fe-reviewer 지적 5 재현: 포인트 입력 오류의 접근성 연결
describe('PaymentForm 회귀: 포인트 입력 오류 접근성', () => {
  it('550 입력 시 aria-invalid="true"이고 aria-describedby가 오류 문구를 가리킨다', async () => {
    renderWithDeps(
      <PaymentForm
        reservationId="r1"
        productName="식빵 모둠"
        quantity={2}
        totalPrice={11500}
        pointBalance={1240}
        onPaid={vi.fn()}
      />,
    );
    const input = screen.getByLabelText('포인트 사용 (100P 단위)');
    await userEvent.type(input, '550');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    const ids = (input.getAttribute('aria-describedby') ?? '').split(/\s+/).filter(Boolean);
    const texts = ids.map((id) => document.getElementById(id)?.textContent ?? '');
    expect(texts).toContain(POINT_NOT_UNIT_MESSAGE);
  });
});
