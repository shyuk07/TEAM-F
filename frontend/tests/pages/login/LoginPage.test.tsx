import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { RouteObject } from 'react-router';
import { LoginPage } from '@/pages/login';
import { ApiError } from '@/shared/api/error';
import { deferred } from '../../features/auth/fakes/deferred';
import { customerUser } from '../../features/auth/fakes/users';
import { anonymousFakes, signedInFakes, type AuthFakes } from '../../support/authFakes';
import { renderRoutesWithAuth } from '../../support/renderWithAuth';
import type { LoginResult } from '@/features/auth/application/ports';
import type { InitialEntry } from 'react-router';
import { SIGNUP_LOGIN_FAILED_NOTICE, type User } from '@/features/auth';

const routes: RouteObject[] = [
  { path: '/login', element: <LoginPage /> },
  { path: '/', element: <p>홈 화면</p> },
  { path: '/owner/today', element: <p>오늘 화면</p> },
  { path: '/owner/offers', element: <p>할인 화면</p> },
  { path: '/signup', element: <p>가입 화면</p> },
  { path: '/password-reset', element: <p>재설정 화면</p> },
];

function renderLogin(opts: { fakes?: AuthFakes; entry?: InitialEntry } = {}) {
  return renderRoutesWithAuth(routes, {
    initialEntries: [opts.entry ?? '/login'],
    fakes: opts.fakes ?? anonymousFakes(),
  });
}

async function fill(email = 'a@b.c', password = 'pw') {
  const user = userEvent.setup();
  await user.type(screen.getByLabelText('이메일'), email);
  await user.type(screen.getByLabelText('비밀번호'), password);
  return user;
}

const submitButton = () => screen.getByRole('button', { name: '로그인' });

describe('LoginPage (A1)', () => {
  it('anonymous: 제목·라벨이 있고 「로그인」 버튼은 비활성이다', () => {
    renderLogin();
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(screen.getByRole('heading', { level: 1, name: '로그인' })).toBeInTheDocument();
    expect(screen.getByLabelText('이메일')).toBeInTheDocument();
    expect(screen.getByLabelText('비밀번호')).toBeInTheDocument();
    expect(submitButton()).toHaveAttribute('aria-disabled', 'true');
  });

  it('두 칸에 입력하면 「로그인」 aria-disabled가 해제된다', async () => {
    renderLogin();
    await fill();
    expect(submitButton()).not.toHaveAttribute('aria-disabled', 'true');
  });

  it('「회원가입」·「비밀번호 재설정」·「사장님이신가요? 입점 신청」은 A2·A3로 가는 링크다', () => {
    renderLogin();
    expect(screen.getByText('계정이 없나요?')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '회원가입' })).toHaveAttribute('href', '/signup');
    expect(screen.getByRole('link', { name: '비밀번호 재설정' })).toHaveAttribute(
      'href',
      '/password-reset',
    );
    expect(screen.getByRole('link', { name: '사장님이신가요? 입점 신청' })).toHaveAttribute(
      'href',
      '/signup?role=owner',
    );
  });

  it('가입 안내는 .cta 한 벌이고 .cta는 display를 직접 정하지 않는다', () => {
    renderLogin();
    const cta = document.querySelector<HTMLElement>('.app > .cta');
    expect(cta).not.toBeNull();
    expect(document.querySelector('.body > .dk')).toBeNull();
    expect(cta?.style.display).toBe('');
    const scope = within(cta as HTMLElement);
    expect(scope.getByText('계정이 없나요?')).toBeInTheDocument();
    expect(scope.getByRole('link', { name: '회원가입' })).toHaveClass('btn');
    expect(scope.getByRole('link', { name: '사장님이신가요? 입점 신청' })).toHaveClass('link');
  });

  it('프레임 안(420px)에는 .dk 요소가 하나도 없다', () => {
    renderLogin();
    expect(document.querySelector('.dk')).toBeNull();
  });

  it('「닫기」(✕)는 /로 가는 링크다', () => {
    renderLogin();
    expect(screen.getByRole('link', { name: '닫기' })).toHaveAttribute('href', '/');
  });

  it('OWNER로 로그인하면 login을 호출하고 /owner/today로 이동한다', async () => {
    const { router, fakes } = renderLogin();
    const user = await fill();
    await user.click(submitButton());
    await waitFor(() => expect(router.state.location.pathname).toBe('/owner/today'));
    expect(fakes.auth.login).toHaveBeenCalledWith('a@b.c', 'pw');
  });

  it('location.state.from이 있으면 OWNER 로그인 뒤 그 경로로 이동한다', async () => {
    const { router } = renderLogin({
      entry: { pathname: '/login', state: { from: '/owner/offers' } },
    });
    const user = await fill();
    await user.click(submitButton());
    await waitFor(() => expect(router.state.location.pathname).toBe('/owner/offers'));
  });

  it('from이 /owner/offers여도 CUSTOMER는 /로 이동한다', async () => {
    const fakes = anonymousFakes();
    fakes.auth.findMe.mockResolvedValue(customerUser);
    const { router } = renderLogin({
      fakes,
      entry: { pathname: '/login', state: { from: '/owner/offers' } },
    });
    const user = await fill();
    await user.click(submitButton());
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
  });

  it('401 INVALID_CREDENTIALS면 명세 문구를 alert로 보이고 입력값·URL을 유지한다', async () => {
    const fakes = anonymousFakes();
    fakes.auth.login.mockRejectedValue(new ApiError(401, 'INVALID_CREDENTIALS', '서버 문구'));
    const { router } = renderLogin({ fakes });
    const user = await fill();
    await user.click(submitButton());
    expect(await screen.findByRole('alert')).toHaveTextContent(
      '이메일 또는 비밀번호가 올바르지 않습니다.',
    );
    expect(screen.getByLabelText('이메일')).toHaveValue('a@b.c');
    expect(screen.getByLabelText('비밀번호')).toHaveValue('pw');
    expect(router.state.location.pathname).toBe('/login');
  });

  it('429 ACCOUNT_LOCKED면 서버 message를 보인다', async () => {
    const fakes = anonymousFakes();
    fakes.auth.login.mockRejectedValue(new ApiError(429, 'ACCOUNT_LOCKED', '잠긴 계정입니다.'));
    renderLogin({ fakes });
    const user = await fill();
    await user.click(submitButton());
    expect(await screen.findByRole('alert')).toHaveTextContent('잠긴 계정입니다.');
  });

  it('로그인 200 뒤 findMe가 403(정지)이면 서버 message를 보이고 세션을 지우며 /login에 머문다', async () => {
    const fakes = anonymousFakes();
    fakes.auth.findMe.mockRejectedValue(new ApiError(403, 'FORBIDDEN', '정지된 계정입니다.'));
    const { router } = renderLogin({ fakes });
    const user = await fill();
    await user.click(submitButton());
    expect(await screen.findByRole('alert')).toHaveTextContent('정지된 계정입니다.');
    expect(fakes.session.clear).toHaveBeenCalled();
    expect(router.state.location.pathname).toBe('/login');
  });

  it('NETWORK_ERROR면 그 문구를 보인다', async () => {
    const fakes = anonymousFakes();
    fakes.auth.login.mockRejectedValue(new ApiError(0, 'NETWORK_ERROR', '네트워크 문구'));
    renderLogin({ fakes });
    const user = await fill();
    await user.click(submitButton());
    expect(await screen.findByRole('alert')).toHaveTextContent('네트워크 문구');
  });

  it('제출 중에는 「처리 중…」·aria-disabled이고 연타해도 login은 1회다', async () => {
    const fakes = anonymousFakes();
    const d = deferred<LoginResult>();
    fakes.auth.login.mockReturnValue(d.promise);
    renderLogin({ fakes });
    const user = await fill();
    await user.click(submitButton());
    const busy = await screen.findByRole('button', { name: '처리 중…' });
    expect(busy).toHaveAttribute('aria-disabled', 'true');
    await user.click(busy);
    expect(fakes.auth.login).toHaveBeenCalledTimes(1);
  });

  it('오류 뒤 다시 제출하면 오류 문구가 사라졌다가 결과에 따라 다시 나타난다', async () => {
    const fakes = anonymousFakes();
    const err = new ApiError(401, 'INVALID_CREDENTIALS', 'x');
    const second = deferred<LoginResult>();
    fakes.auth.login.mockRejectedValueOnce(err).mockReturnValueOnce(second.promise);
    renderLogin({ fakes });
    const user = await fill();
    await user.click(submitButton());
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    await user.click(submitButton());
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
    second.reject(err);
    expect(await screen.findByRole('alert')).toHaveTextContent(
      '이메일 또는 비밀번호가 올바르지 않습니다.',
    );
  });

  it('이메일 칸에서 Enter로 제출한다', async () => {
    const { fakes } = renderLogin();
    const user = userEvent.setup();
    await user.type(screen.getByLabelText('비밀번호'), 'pw');
    await user.type(screen.getByLabelText('이메일'), 'a@b.c{enter}');
    await waitFor(() => expect(fakes.auth.login).toHaveBeenCalledWith('a@b.c', 'pw'));
  });

  it('이미 로그인한 OWNER가 /login에 오면 /owner/today로 이동한다', async () => {
    const { router } = renderLogin({ fakes: signedInFakes() });
    await waitFor(() => expect(router.state.location.pathname).toBe('/owner/today'));
  });

  it('이미 로그인한 CUSTOMER가 /login에 오면 /로 이동한다', async () => {
    const { router } = renderLogin({ fakes: signedInFakes(customerUser) });
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
  });

  it('세션 확인 중에는 폼도 이동도 없고 aria-busy 프레임만 있다', () => {
    const fakes = signedInFakes();
    const d = deferred<User>();
    fakes.auth.findMe.mockReturnValue(d.promise);
    const { router } = renderLogin({ fakes });
    expect(document.querySelector('[aria-busy="true"]')).not.toBeNull();
    expect(screen.queryByRole('heading', { name: '로그인' })).not.toBeInTheDocument();
    expect(screen.queryByLabelText('이메일')).not.toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/login');
  });
});

describe('LoginPage (A1) 계정 화면 연결 (auth-account D-7·D-10·D-17·D-25)', () => {
  const fromOffers: InitialEntry = { pathname: '/login', state: { from: '/owner/offers' } };

  it('state.from이 있을 때 「회원가입」을 누르면 A2로 가고 from을 넘긴다', async () => {
    const { router } = renderLogin({ entry: fromOffers });
    await userEvent.setup().click(screen.getByRole('link', { name: '회원가입' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/signup'));
    expect(router.state.location.state).toEqual({ from: '/owner/offers' });
  });

  it('state.from이 있을 때 「사장님이신가요? 입점 신청」을 누르면 ?role=owner A2로 가고 from을 넘긴다', async () => {
    const { router } = renderLogin({ entry: fromOffers });
    await userEvent.setup().click(screen.getByRole('link', { name: '사장님이신가요? 입점 신청' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/signup'));
    expect(router.state.location.search).toBe('?role=owner');
    expect(router.state.location.state).toEqual({ from: '/owner/offers' });
  });

  it('state.from이 있을 때 「비밀번호 재설정」을 누르면 A3로 가고 from을 넘긴다', async () => {
    const { router } = renderLogin({ entry: fromOffers });
    await userEvent.setup().click(screen.getByRole('link', { name: '비밀번호 재설정' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/password-reset'));
    expect(router.state.location.state).toEqual({ from: '/owner/offers' });
  });

  it('notice가 passwordReset이면 「새 비밀번호로 로그인하세요」를 status로 보인다', () => {
    renderLogin({ entry: { pathname: '/login', state: { notice: 'passwordReset' } } });
    expect(screen.getByRole('status')).toHaveTextContent('새 비밀번호로 로그인하세요');
  });

  it('notice가 signupLoginFailed이면 가입 뒤 로그인 안내를 status로 보인다', () => {
    renderLogin({ entry: { pathname: '/login', state: { notice: 'signupLoginFailed' } } });
    expect(screen.getByRole('status')).toHaveTextContent(SIGNUP_LOGIN_FAILED_NOTICE);
  });

  it('notice가 없으면 status 안내가 없다', () => {
    renderLogin();
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
  });

  it("state.entry가 'reservation'이면 제목 바로 아래 「예약을 이어가려면 로그인하세요.」", () => {
    renderLogin({
      entry: { pathname: '/login', state: { from: '/offers/1', entry: 'reservation' } },
    });
    const guide = screen.getByText('예약을 이어가려면 로그인하세요.');
    expect(screen.getByRole('heading', { level: 1, name: '로그인' }).nextElementSibling).toBe(
      guide,
    );
  });

  // 골격에서도 통과한다(안내가 없는 현재 동작). entry가 없을 때 안내가 생기지 않음을 고정한다.
  it('state.entry가 없으면 진입 안내 줄이 없다', () => {
    renderLogin({ entry: { pathname: '/login', state: { from: '/me' } } });
    expect(screen.queryByText('예약을 이어가려면 로그인하세요.')).not.toBeInTheDocument();
    expect(screen.queryByText('예약 내역을 보려면 로그인하세요.')).not.toBeInTheDocument();
  });

  it('429 ACCOUNT_LOCKED면 서버 문구를 글자 그대로 보이고 입력을 유지한 채 「로그인」이 다시 활성이다', async () => {
    const fakes = anonymousFakes();
    const message = '로그인 시도가 너무 많아 계정이 잠겼습니다. 9분 뒤에 다시 시도해 주세요.';
    fakes.auth.login.mockRejectedValue(new ApiError(429, 'ACCOUNT_LOCKED', message));
    renderLogin({ fakes });
    const user = await fill();
    await user.click(submitButton());
    expect(await screen.findByRole('alert')).toHaveTextContent(message);
    expect(screen.getByLabelText('이메일')).toHaveValue('a@b.c');
    expect(screen.getByLabelText('비밀번호')).toHaveValue('pw');
    expect(submitButton()).not.toHaveAttribute('aria-disabled', 'true');
  });
});
