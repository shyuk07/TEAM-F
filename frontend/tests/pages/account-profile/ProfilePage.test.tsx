import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { InitialEntry, RouteObject } from 'react-router';
import { AccountLayout } from '@/app/layouts/AccountLayout';
import { routes } from '@/app/router/routes';
import { useAuth, type User } from '@/features/auth';
import { ProfilePage } from '@/pages/account-profile';
import { ApiError } from '@/shared/api/error';
import { deferred } from '../../features/auth/fakes/deferred';
import {
  adminUser,
  customerUser,
  legacyCustomerUser,
  ownerUser,
} from '../../features/auth/fakes/users';
import { signedInFakes, type AuthFakes } from '../../support/authFakes';
import { renderRoutesWithAuth } from '../../support/renderWithAuth';

const customer: User = { ...customerUser, name: '김고객', phone: '010-1' };
const owner: User = { ...ownerUser, phone: '010-1' };

function renderProfile(opts: { fakes?: AuthFakes; entry?: InitialEntry } = {}) {
  return renderRoutesWithAuth(routes, {
    initialEntries: [opts.entry ?? '/account/profile'],
    fakes: opts.fakes ?? signedInFakes(customer),
  });
}

async function ready() {
  await screen.findByRole('heading', { name: '프로필 변경' });
  return userEvent.setup();
}

const saveButtons = () => screen.getAllByRole('button', { name: '저장' });

function expectAllDisabled(buttons: HTMLElement[], disabled: boolean) {
  for (const b of buttons) {
    if (disabled) expect(b).toHaveAttribute('aria-disabled', 'true');
    else expect(b).not.toHaveAttribute('aria-disabled', 'true');
  }
}

async function changePhone(user: ReturnType<typeof userEvent.setup>, phone = '010-2') {
  const input = screen.getByLabelText('전화번호');
  await user.clear(input);
  await user.type(input, phone);
}

function PhoneProbe() {
  const { state } = useAuth();
  return (
    <output data-testid="probe">{state.status === 'authenticated' ? state.user.phone : ''}</output>
  );
}

describe('ProfilePage (C8)', () => {
  it('CUSTOMER: 제목과 읽기 전용 이메일 칸(in ro)이 있다', async () => {
    renderProfile();
    await ready();
    expect(screen.getByRole('heading', { level: 1, name: '프로필 변경' })).toBeInTheDocument();
    const email = screen.getByLabelText('이메일 (변경 불가)');
    expect(email).toHaveAttribute('readonly');
    expect(email).toHaveClass('in', 'ro');
    expect(email).toHaveValue('customer@test.com');
  });

  it('이름·전화번호에 현재 값이 있고 「저장」 두 벌이 비활성이다', async () => {
    renderProfile();
    await ready();
    expect(screen.getByLabelText('이름')).toHaveValue('김고객');
    expect(screen.getByLabelText('전화번호')).toHaveValue('010-1');
    const buttons = saveButtons();
    expect(buttons).toHaveLength(2);
    expectAllDisabled(buttons, true);
  });

  it('전화를 바꾸면 활성이고 제출하면 updateProfile({phone})을 정확히 1회 부른다', async () => {
    const { fakes } = renderProfile();
    const user = await ready();
    await changePhone(user);
    expectAllDisabled(saveButtons(), false);
    await user.click(saveButtons()[0]);
    await waitFor(() => expect(fakes.account.updateProfile).toHaveBeenCalledTimes(1));
    expect(fakes.account.updateProfile.mock.calls[0]?.[0]).toEqual({ phone: '010-2' });
  });

  it('성공하면 「저장했어요」가 보이고 「저장」이 다시 비활성이며 URL은 그대로다', async () => {
    const { router } = renderProfile();
    const user = await ready();
    await changePhone(user);
    await user.click(saveButtons()[0]);
    expect(await screen.findByRole('status')).toHaveTextContent('저장했어요');
    expectAllDisabled(saveButtons(), true);
    expect(router.state.location.pathname).toBe('/account/profile');
  });

  it('성공 뒤 같은 트리의 useAuth 소비자가 새 전화번호를 본다', async () => {
    const probeRoutes: RouteObject[] = [
      {
        element: <AccountLayout />,
        children: [
          {
            path: '/account/profile',
            element: (
              <>
                <ProfilePage />
                <PhoneProbe />
              </>
            ),
          },
        ],
      },
    ];
    renderRoutesWithAuth(probeRoutes, {
      initialEntries: ['/account/profile'],
      fakes: signedInFakes(customer),
    });
    const user = await ready();
    expect(screen.getByTestId('probe')).toHaveTextContent('010-1');
    await changePhone(user);
    await user.click(saveButtons()[0]);
    await waitFor(() => expect(screen.getByTestId('probe')).toHaveTextContent('010-2'));
  });

  it('OWNER: 「상호 (변경 불가)」는 읽기 전용이고 「이름」 칸이 없으며 전화 변경에 name이 없다', async () => {
    const { fakes } = renderProfile({ fakes: signedInFakes(owner) });
    const user = await ready();
    const shop = screen.getByLabelText('상호 (변경 불가)');
    expect(shop).toHaveAttribute('readonly');
    expect(shop).toHaveClass('in', 'ro');
    expect(shop).toHaveValue('망원베이커리');
    expect(screen.queryByLabelText('이름')).not.toBeInTheDocument();
    await changePhone(user);
    await user.click(saveButtons()[0]);
    await waitFor(() => expect(fakes.account.updateProfile).toHaveBeenCalledTimes(1));
    expect(fakes.account.updateProfile.mock.calls[0]?.[0]).toEqual({ phone: '010-2' });
  });

  it('「뒤로」: OWNER는 from 또는 /owner/today, CUSTOMER는 /로 간다', async () => {
    const a = renderProfile({
      fakes: signedInFakes(owner),
      entry: { pathname: '/account/profile', state: { from: '/owner/offers' } },
    });
    await ready();
    expect(screen.getByRole('link', { name: '뒤로' })).toHaveAttribute('href', '/owner/offers');
    a.unmount();

    const b = renderProfile({ fakes: signedInFakes(owner) });
    await ready();
    expect(screen.getByRole('link', { name: '뒤로' })).toHaveAttribute('href', '/owner/today');
    b.unmount();

    renderProfile({ fakes: signedInFakes(customer) });
    await ready();
    expect(screen.getByRole('link', { name: '뒤로' })).toHaveAttribute('href', '/');
  });

  it('전화번호를 공백으로 바꾸면 비활성이다', async () => {
    renderProfile();
    const user = await ready();
    await changePhone(user, '   ');
    expectAllDisabled(saveButtons(), true);
  });

  it('이름이 null인 CUSTOMER가 전화만 바꾸면 비활성이다(REQ-23)', async () => {
    renderProfile({ fakes: signedInFakes({ ...legacyCustomerUser, phone: '010-1' }) });
    const user = await ready();
    await changePhone(user);
    expectAllDisabled(saveButtons(), true);
  });

  it('ADMIN은 「이름」을 편집할 수 있다', async () => {
    renderProfile({ fakes: signedInFakes(adminUser) });
    await ready();
    const name = screen.getByLabelText('이름');
    expect(name).not.toHaveAttribute('readonly');
    expect(screen.queryByLabelText('상호 (변경 불가)')).not.toBeInTheDocument();
  });

  it('400이면 서버 문구를 보인다', async () => {
    const fakes = signedInFakes(customer);
    fakes.account.updateProfile.mockRejectedValue(
      new ApiError(400, 'VALIDATION_ERROR', '서버 규칙 문구'),
    );
    renderProfile({ fakes });
    const user = await ready();
    await changePhone(user);
    await user.click(saveButtons()[0]);
    expect(await screen.findByRole('alert')).toHaveTextContent('서버 규칙 문구');
  });

  it('401 TOKEN_REVOKED면 세션을 지우고 /login으로 가며 from이 /account/profile이다', async () => {
    const fakes = signedInFakes(customer);
    fakes.account.updateProfile.mockRejectedValue(
      new ApiError(401, 'TOKEN_REVOKED', '폐기된 토큰입니다.'),
    );
    const { router } = renderProfile({ fakes });
    const user = await ready();
    await changePhone(user);
    await user.click(saveButtons()[0]);
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    expect(fakes.session.clear).toHaveBeenCalled();
    expect(router.state.location.state).toMatchObject({ from: '/account/profile' });
  });

  it('403이면 「정지된 계정입니다.」를 보인다', async () => {
    const fakes = signedInFakes(customer);
    fakes.account.updateProfile.mockRejectedValue(
      new ApiError(403, 'FORBIDDEN', '정지된 계정입니다.'),
    );
    renderProfile({ fakes });
    const user = await ready();
    await changePhone(user);
    await user.click(saveButtons()[0]);
    expect(await screen.findByRole('alert')).toHaveTextContent('정지된 계정입니다.');
  });

  it('제출 중에는 「처리 중…」이고 연타해도 1회이며, 완료 표시는 다시 입력하면 사라진다', async () => {
    const fakes = signedInFakes(customer);
    const d = deferred<User>();
    fakes.account.updateProfile.mockReturnValueOnce(d.promise);
    renderProfile({ fakes });
    const user = await ready();
    await changePhone(user);
    await user.click(saveButtons()[0]);
    const busy = await screen.findAllByRole('button', { name: '처리 중…' });
    expect(busy).toHaveLength(2);
    expectAllDisabled(busy, true);
    await user.click(busy[0]);
    await user.click(busy[1]);
    expect(fakes.account.updateProfile).toHaveBeenCalledTimes(1);
    d.resolve({ ...customer, phone: '010-2' });
    expect(await screen.findByRole('status')).toHaveTextContent('저장했어요');
    await user.type(screen.getByLabelText('전화번호'), '3');
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });
});
