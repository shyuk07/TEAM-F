import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { InitialEntry, RouteObject } from 'react-router';
import { SIGNUP_LOGIN_FAILED_NOTICE, type User } from '@/features/auth';
import { PASSWORD_BLANK_MESSAGE } from '@/features/auth/domain/accountMessages';
import { LoginPage } from '@/pages/login';
import { SignupPage } from '@/pages/signup';
import { ApiError } from '@/shared/api/error';
import { deferred } from '../../features/auth/fakes/deferred';
import { customerUser, ownerUser } from '../../features/auth/fakes/users';
import { anonymousFakes, signedInFakes, type AuthFakes } from '../../support/authFakes';
import { renderRoutesWithAuth } from '../../support/renderWithAuth';

const routes: RouteObject[] = [
  { path: '/signup', element: <SignupPage /> },
  { path: '/login', element: <LoginPage /> },
  { path: '/', element: <p>홈 화면</p> },
  { path: '/owner/today', element: <p>오늘 화면</p> },
  { path: '/offers/1', element: <p>상품 화면</p> },
];

function renderSignup(opts: { fakes?: AuthFakes; entry?: InitialEntry } = {}) {
  return renderRoutesWithAuth(routes, {
    initialEntries: [opts.entry ?? '/signup'],
    fakes: opts.fakes ?? anonymousFakes(),
  });
}

/** 세션 확인이 끝나 회원가입 화면이 보일 때까지 기다린다. */
async function ready() {
  await screen.findByRole('heading', { name: '회원가입' });
  return userEvent.setup();
}

async function fill(
  user: ReturnType<typeof userEvent.setup>,
  values: { name?: string; email?: string; password?: string; phone?: string } = {},
) {
  const nameInput =
    screen.queryByLabelText('이름 *') ?? screen.getByLabelText('상호(상점명으로 쓰임) *');
  await user.type(nameInput, values.name ?? '홍길동');
  await user.type(screen.getByLabelText('이메일 *'), values.email ?? 'a@b.c');
  await user.type(screen.getByLabelText('비밀번호 * (8자 이상)'), values.password ?? 'pw123456');
  await user.type(screen.getByLabelText('전화번호 *'), values.phone ?? '010-1');
}

const submitButton = () => screen.getByRole('button', { name: '가입하기' });

function expectDisabled(button: HTMLElement, disabled: boolean) {
  if (disabled) expect(button).toHaveAttribute('aria-disabled', 'true');
  else expect(button).not.toHaveAttribute('aria-disabled', 'true');
}

function customerSignupFakes() {
  const fakes = anonymousFakes();
  fakes.auth.findMe.mockResolvedValue(customerUser);
  return fakes;
}

describe('SignupPage (A2)', () => {
  it('제목 「회원가입」과 /login으로 가는 「뒤로」 링크가 있다', async () => {
    renderSignup();
    await ready();
    expect(screen.getByRole('heading', { level: 1, name: '회원가입' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '뒤로' })).toHaveAttribute('href', '/login');
  });

  it('라벨이 모두 있고 처음에는 「일반 고객」이 선택되어 있다', async () => {
    renderSignup();
    await ready();
    expect(screen.getByText('어떻게 이용하시나요? *')).toBeInTheDocument();
    expect(screen.getByLabelText('이름 *')).toBeInTheDocument();
    expect(screen.getByLabelText('이메일 *')).toBeInTheDocument();
    expect(screen.getByLabelText('비밀번호 * (8자 이상)')).toBeInTheDocument();
    expect(screen.getByLabelText('전화번호 *')).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /^일반 고객/ })).toHaveAttribute(
      'aria-checked',
      'true',
    );
    expect(screen.getByRole('radio', { name: /^상점주/ })).toHaveAttribute('aria-checked', 'false');
  });

  it('계정 유형 안내 문구가 있다', async () => {
    renderSignup();
    await ready();
    expect(
      screen.getByText(
        '한 계정은 한 가지 유형이에요. 상점주는 관리자 승인 후 상점을 열 수 있어요.',
      ),
    ).toBeInTheDocument();
  });

  it('/signup?role=owner면 「상점주」가 선택되고 이름 라벨이 「상호(상점명으로 쓰임) *」다', async () => {
    renderSignup({ entry: '/signup?role=owner' });
    await ready();
    expect(screen.getByRole('radio', { name: /^상점주/ })).toHaveAttribute('aria-checked', 'true');
    expect(screen.getByLabelText('상호(상점명으로 쓰임) *')).toBeInTheDocument();
  });

  it('「상점주」를 누르면 라벨이 바뀌고 「일반 고객」을 다시 누르면 「이름 *」으로 돌아온다', async () => {
    renderSignup();
    const user = await ready();
    await user.click(screen.getByRole('radio', { name: /^상점주/ }));
    expect(screen.getByLabelText('상호(상점명으로 쓰임) *')).toBeInTheDocument();
    await user.click(screen.getByRole('radio', { name: /^일반 고객/ }));
    expect(screen.getByLabelText('이름 *')).toBeInTheDocument();
  });

  it('「가입하기」는 .cta 안 한 벌이고 처음에는 비활성이다', async () => {
    renderSignup();
    await ready();
    const button = submitButton();
    expect(button.closest('.cta')).not.toBeNull();
    expect(document.querySelector('.dk')).toBeNull();
    expectDisabled(button, true);
  });

  it('모두 입력하면 활성이고 비밀번호가 7자면 비활성이다', async () => {
    renderSignup();
    const user = await ready();
    await fill(user);
    expectDisabled(submitButton(), false);
    await user.clear(screen.getByLabelText('비밀번호 * (8자 이상)'));
    await user.type(screen.getByLabelText('비밀번호 * (8자 이상)'), '1234567');
    expectDisabled(submitButton(), true);
  });

  it('비밀번호가 공백 8칸이면 비밀번호 칸 아래 임시 문구가 보이고 비활성이다', async () => {
    renderSignup();
    const user = await ready();
    await fill(user, { password: '        ' });
    expect(screen.getByText(PASSWORD_BLANK_MESSAGE)).toBeInTheDocument();
    expectDisabled(submitButton(), true);
  });

  it('입력 칸 maxLength: 이름·전화 100, 이메일 255', async () => {
    renderSignup();
    await ready();
    expect(screen.getByLabelText('이름 *')).toHaveAttribute('maxlength', '100');
    expect(screen.getByLabelText('전화번호 *')).toHaveAttribute('maxlength', '100');
    expect(screen.getByLabelText('이메일 *')).toHaveAttribute('maxlength', '255');
  });

  it('제출하면 앞뒤 공백을 지운 값으로 signup을 1회 부르고 이어서 같은 이메일·비밀번호로 로그인한다', async () => {
    const { fakes } = renderSignup({ fakes: customerSignupFakes() });
    const user = await ready();
    await fill(user, { name: ' 홍길동 ', email: ' a@b.c ', phone: ' 010-1 ' });
    await user.click(submitButton());
    await waitFor(() => expect(fakes.auth.login).toHaveBeenCalledWith('a@b.c', 'pw123456'));
    expect(fakes.account.signup).toHaveBeenCalledTimes(1);
    expect(fakes.account.signup.mock.calls[0]?.[0]).toEqual({
      email: 'a@b.c',
      password: 'pw123456',
      name: '홍길동',
      phone: '010-1',
      role: 'CUSTOMER',
    });
  });

  it('상점주로 가입하고 로그인 결과가 OWNER면 /owner/today로 이동한다', async () => {
    const fakes = anonymousFakes();
    fakes.auth.findMe.mockResolvedValue(ownerUser);
    const { router } = renderSignup({ fakes, entry: '/signup?role=owner' });
    const user = await ready();
    await fill(user, { name: '망원베이커리' });
    await user.click(submitButton());
    await waitFor(() => expect(router.state.location.pathname).toBe('/owner/today'));
    expect(fakes.account.signup.mock.calls[0]?.[0]).toMatchObject({ role: 'OWNER' });
  });

  it('state.from=/offers/1로 들어와 고객으로 가입하면 /offers/1로 이동한다', async () => {
    const { router } = renderSignup({
      fakes: customerSignupFakes(),
      entry: { pathname: '/signup', state: { from: '/offers/1' } },
    });
    const user = await ready();
    await fill(user);
    await user.click(submitButton());
    await waitFor(() => expect(router.state.location.pathname).toBe('/offers/1'));
  });

  it('409면 이메일 칸 바로 아래 「이미 가입된 이메일입니다.」가 보이고 입력값·URL을 유지한다', async () => {
    const fakes = customerSignupFakes();
    fakes.account.signup.mockRejectedValue(new ApiError(409, 'EMAIL_DUPLICATED', '서버 문구'));
    const { router } = renderSignup({ fakes });
    const user = await ready();
    await fill(user);
    await user.click(submitButton());
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('이미 가입된 이메일입니다.');
    const email = screen.getByLabelText('이메일 *');
    const password = screen.getByLabelText('비밀번호 * (8자 이상)');
    // 이메일 칸 뒤, 비밀번호 칸 앞(이메일 칸 묶음)
    expect(email.compareDocumentPosition(alert) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(alert.compareDocumentPosition(password) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(email).toHaveValue('a@b.c');
    expect(screen.getByLabelText('이름 *')).toHaveValue('홍길동');
    expect(router.state.location.pathname).toBe('/signup');
    expect(fakes.auth.login).not.toHaveBeenCalled();
  });

  it('400 VALIDATION_ERROR면 폼 오류 자리에 서버 문구를 보인다', async () => {
    const fakes = customerSignupFakes();
    fakes.account.signup.mockRejectedValue(
      new ApiError(400, 'VALIDATION_ERROR', '이메일 형식이 올바르지 않습니다.'),
    );
    renderSignup({ fakes });
    const user = await ready();
    await fill(user);
    await user.click(submitButton());
    expect(await screen.findByRole('alert')).toHaveTextContent('이메일 형식이 올바르지 않습니다.');
  });

  it('가입 성공 뒤 로그인이 실패하면 /login으로 가서 안내를 보이고 from을 유지한다', async () => {
    const fakes = customerSignupFakes();
    fakes.auth.login.mockRejectedValue(new ApiError(0, 'NETWORK_ERROR', '네트워크 문구'));
    const { router } = renderSignup({
      fakes,
      entry: { pathname: '/signup', state: { from: '/offers/1' } },
    });
    const user = await ready();
    await fill(user);
    await user.click(submitButton());
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    expect(await screen.findByRole('status')).toHaveTextContent(SIGNUP_LOGIN_FAILED_NOTICE);
    expect(router.state.location.state).toMatchObject({ from: '/offers/1' });
  });

  it('제출 중에는 「처리 중…」·aria-disabled이고 연타해도 signup은 1회다', async () => {
    const fakes = customerSignupFakes();
    const d = deferred<void>();
    fakes.account.signup.mockReturnValue(d.promise);
    renderSignup({ fakes });
    const user = await ready();
    await fill(user);
    await user.click(submitButton());
    const busy = await screen.findByRole('button', { name: '처리 중…' });
    expectDisabled(busy, true);
    await user.click(busy);
    expect(fakes.account.signup).toHaveBeenCalledTimes(1);
  });

  it('이미 로그인한 OWNER는 /owner/today로 가고, 세션 확인 중에는 aria-busy 프레임만 있다', async () => {
    const first = renderSignup({ fakes: signedInFakes() });
    await waitFor(() => expect(first.router.state.location.pathname).toBe('/owner/today'));
    first.unmount();

    const fakes = signedInFakes();
    fakes.auth.findMe.mockReturnValue(deferred<User>().promise);
    const second = renderSignup({ fakes });
    expect(document.querySelector('[aria-busy="true"]')).not.toBeNull();
    expect(screen.queryByRole('heading', { name: '회원가입' })).not.toBeInTheDocument();
    expect(second.router.state.location.pathname).toBe('/signup');
  });
});
