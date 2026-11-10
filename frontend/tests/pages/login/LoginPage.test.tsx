import { screen, waitFor } from '@testing-library/react';
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
import type { User } from '@/features/auth';

const routes: RouteObject[] = [
  { path: '/login', element: <LoginPage /> },
  { path: '/', element: <p>홈 화면</p> },
  { path: '/owner/today', element: <p>오늘 화면</p> },
  { path: '/owner/offers', element: <p>할인 화면</p> },
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

  it('회원가입·비밀번호 재설정·입점 신청 자리가 있고 눌러도 URL이 바뀌지 않는다', async () => {
    const { router } = renderLogin();
    const user = userEvent.setup();
    expect(screen.getByText('계정이 없나요?')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '회원가입' }));
    await user.click(screen.getByText('비밀번호 재설정'));
    await user.click(screen.getByText('사장님이신가요? 입점 신청'));
    expect(router.state.location.pathname).toBe('/login');
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
