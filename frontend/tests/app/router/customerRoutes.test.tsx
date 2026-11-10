import { screen, waitFor } from '@testing-library/react';
import { routes } from '@/app/router/routes';
import { customerUser } from '../../features/auth/fakes/users';
import { makeReservation } from '../../features/reservations/fakes/reservations';
import { anonymousFakes, signedInFakes } from '../../support/authFakes';
import { createFakes, renderRoutesWithDeps, type DepsFakes } from '../../support/renderWithDeps';

function customerFakes(): DepsFakes {
  const fakes = createFakes(signedInFakes(customerUser));
  fakes.reservations.get.mockResolvedValue(makeReservation({ status: 'RESERVED' }));
  return fakes;
}

describe('고객 라우트', () => {
  it.each(['/me/reservations', '/checkout/r1', '/checkout/r1/complete'])(
    '%s는 비로그인이면 /login으로 이동하고 from을 유지한다',
    async (path) => {
      const { router } = renderRoutesWithDeps(routes, {
        initialEntries: [path],
        fakes: createFakes(anonymousFakes()),
      });
      await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
      expect(router.state.location.state).toEqual({ from: path });
    },
  );

  it('/me/reservations는 CUSTOMER에게 「내 예약」 화면을 보여 준다', async () => {
    renderRoutesWithDeps(routes, {
      initialEntries: ['/me/reservations'],
      fakes: customerFakes(),
    });
    expect(await screen.findByRole('heading', { name: '내 예약' })).toBeInTheDocument();
  });

  it('/checkout/r1/complete는 CUSTOMER에게 픽업 코드를 보여 준다', async () => {
    renderRoutesWithDeps(routes, {
      initialEntries: ['/checkout/r1/complete'],
      fakes: customerFakes(),
    });
    expect(await screen.findByText('A12345')).toBeInTheDocument();
  });

  it('/me/reservations는 OWNER면 /로 이동한다', async () => {
    const { router } = renderRoutesWithDeps(routes, {
      initialEntries: ['/me/reservations'],
      fakes: createFakes(signedInFakes()),
    });
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
  });
});
