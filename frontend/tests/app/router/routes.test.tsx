import { screen, waitFor } from '@testing-library/react';
import { routes } from '@/app/router/routes';
import { customerUser } from '../../features/auth/fakes/users';
import { anonymousFakes, signedInFakes, type AuthFakes } from '../../support/authFakes';
import { renderRoutesWithAuth } from '../../support/renderWithAuth';

function renderAt(path: string, fakes: AuthFakes = signedInFakes()) {
  return renderRoutesWithAuth(routes, { initialEntries: [path], fakes }).router;
}

describe('routes', () => {
  it('/owner는 /owner/today로 이동한다', () => {
    const router = renderAt('/owner');
    expect(router.state.location.pathname).toBe('/owner/today');
  });

  it.each([
    ['/owner/today', 'O1 오늘'],
    ['/owner/offers', 'O2 할인'],
    ['/owner/store', 'O4 매장'],
  ])('%s: 제목 「%s」과 TabBar·TopNav 링크가 있다', async (path, title) => {
    renderAt(path);
    expect(await screen.findByRole('heading', { name: title })).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: '오늘' })).toHaveLength(2);
  });

  it.each([
    ['/owner/offers/new', 'O3 할인 등록'],
    ['/owner/products/new', 'O6 상품 등록'],
    ['/owner/products/p1', 'O11 상품 수정'],
  ])('%s: 제목 「%s」이 있고 TabBar는 없다(TopNav만)', async (path, title) => {
    renderAt(path);
    expect(await screen.findByRole('heading', { name: title })).toBeInTheDocument();
    expect(screen.getAllByRole('link', { name: '오늘' })).toHaveLength(1);
  });

  it('/owner/products/p1은 productId를 표시한다', async () => {
    renderAt('/owner/products/p1');
    expect(await screen.findByText(/p1/)).toBeInTheDocument();
  });

  it('/login은 셸 없이 로그인 자리를 그린다', () => {
    renderAt('/login', anonymousFakes());
    expect(screen.queryAllByRole('link', { name: '오늘' })).toHaveLength(0);
    expect(document.querySelector('a[href="/owner/today"]')).toBeNull();
    expect(screen.getByRole('heading', { name: '로그인' })).toBeInTheDocument();
  });

  it('/는 「마감 직전」을 보여 준다', () => {
    renderAt('/');
    expect(screen.getByRole('heading', { name: '마감 직전' })).toBeInTheDocument();
  });

  it.each(['/nope', '/owner/nope'])('%s는 /로 이동한다', (path) => {
    const router = renderAt(path);
    expect(router.state.location.pathname).toBe('/');
  });

  it('/owner/today는 비로그인이면 /login으로 이동한다', async () => {
    const router = renderAt('/owner/today', anonymousFakes());
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
  });

  it('/owner/store는 CUSTOMER면 /로 이동한다', async () => {
    const router = renderAt('/owner/store', signedInFakes(customerUser));
    await waitFor(() => expect(router.state.location.pathname).toBe('/'));
  });

  it('/login은 이미 로그인한 OWNER를 /owner/today로 보낸다', async () => {
    const router = renderAt('/login', signedInFakes());
    await waitFor(() => expect(router.state.location.pathname).toBe('/owner/today'));
  });
});

describe('routes: 계정 화면 (auth-account §4)', () => {
  it('/signup은 비로그인이면 「회원가입」을 보여 준다', async () => {
    renderAt('/signup', anonymousFakes());
    expect(await screen.findByRole('heading', { name: '회원가입' })).toBeInTheDocument();
  });

  it('/password-reset은 비로그인이면 「비밀번호 재설정」을 보여 준다', async () => {
    renderAt('/password-reset', anonymousFakes());
    expect(await screen.findByRole('heading', { name: '비밀번호 재설정' })).toBeInTheDocument();
  });

  it('/account/profile은 비로그인이면 /login으로 이동한다', async () => {
    const router = renderAt('/account/profile', anonymousFakes());
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
  });

  it('/account/profile은 OWNER에게 「프로필 변경」을 보여 준다', async () => {
    renderAt('/account/profile', signedInFakes());
    expect(await screen.findByRole('heading', { name: '프로필 변경' })).toBeInTheDocument();
  });

  it('/account/password는 CUSTOMER에게 「비밀번호 변경」을 보여 준다', async () => {
    renderAt('/account/password', signedInFakes(customerUser));
    expect(await screen.findByRole('heading', { name: '비밀번호 변경' })).toBeInTheDocument();
  });

  it('/account는 /account/profile로 이동한다', async () => {
    const router = renderAt('/account', signedInFakes());
    await waitFor(() => expect(router.state.location.pathname).toBe('/account/profile'));
  });

  it('/signup은 이미 로그인한 OWNER를 /owner/today로 보낸다', async () => {
    const router = renderAt('/signup', signedInFakes());
    await waitFor(() => expect(router.state.location.pathname).toBe('/owner/today'));
  });
});
