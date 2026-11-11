import { screen, waitFor, within } from '@testing-library/react';
import { FakeStoreRepository } from '../../entities/store/fakes/fakeStoreRepository.fake';
import { ownerUser } from '../../features/auth/fakes/users';
import { renderRoutesWithOwnerStore } from '../../support/renderWithOwnerStore';
import { routes } from '@/app/router/routes';
import { customerUser } from '../../features/auth/fakes/users';
import { anonymousFakes, signedInFakes, type AuthFakes } from '../../support/authFakes';
import { renderRoutesWithAuth } from '../../support/renderWithAuth';
import { createFakes, renderRoutesWithDeps } from '../../support/renderWithDeps';
import { renderRoutesWithOfferDetail } from '../../support/renderWithOfferDetail';
import { makeOfferDetail } from '../../features/offers/fakes/offerDetails';

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

  // D-27: 기존 「/는 「마감 직전」을 보여 준다」를 교체
  it('/는 heading 「마감직전」과 고객 탭 바(홈 현재)를 보여 준다', async () => {
    renderAt('/', anonymousFakes());
    expect(await screen.findByRole('heading', { name: '마감직전' })).toBeInTheDocument();
    const nav = screen.getByRole('navigation', { name: '고객 메뉴' });
    expect(within(nav).getByRole('link', { name: '홈' })).toHaveAttribute('aria-current', 'page');
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

describe('routes: 고객 셸 (customer-home §4)', () => {
  // 자리 page → 실제 C2(offers.md §2.3, customer-home §5.3). 의미(공개 접근, offerId로 조회, 탭 바 없음)는 그대로.
  it('/offers/abc는 비로그인이면 C2 할인 상세를 abc로 조회해 보이고 탭 바는 없다', async () => {
    const fakes = anonymousFakes();
    fakes.offers.findById.mockResolvedValue(makeOfferDetail({}, { id: 'abc' }));
    const { router } = renderRoutesWithOfferDetail(routes, {
      initialEntries: ['/offers/abc'],
      fakes,
    });
    expect(
      await screen.findByRole('heading', { level: 1, name: '소금빵 세트' }),
    ).toBeInTheDocument();
    expect(router.state.location.pathname).toBe('/offers/abc');
    expect(fakes.offers.findById.mock.calls[0]?.[0]).toBe('abc');
    expect(screen.queryByRole('navigation', { name: '고객 메뉴' })).not.toBeInTheDocument();
  });

  it('/reservations는 CUSTOMER에게 C5 내 예약 화면과 탭 「내 예약」 현재를 보인다', async () => {
    // 실제 C5 화면은 예약 저장소가 필요해 예약·결제 가짜 포트까지 넣은 도우미로 렌더한다
    renderRoutesWithDeps(routes, {
      initialEntries: ['/reservations'],
      fakes: createFakes(signedInFakes(customerUser)),
    });
    expect(await screen.findByRole('heading', { name: '내 예약', level: 1 })).toBeInTheDocument();
    const nav = screen.getByRole('navigation', { name: '고객 메뉴' });
    expect(within(nav).getByRole('link', { name: '내 예약' })).toHaveAttribute(
      'aria-current',
      'page',
    );
  });

  it('/me/points는 비로그인이면 /login으로 이동한다', async () => {
    const router = renderAt('/me/points', anonymousFakes());
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
  });
});

describe('routes stores 화면 추가', () => {
  function renderStoreAt(
    path: string,
    authFakes = signedInFakes(),
    repo = new FakeStoreRepository(),
  ) {
    return renderRoutesWithOwnerStore(routes, { initialEntries: [path], fakes: authFakes, repo });
  }

  const noneRepo = () => {
    const repo = new FakeStoreRepository();
    repo.findMine.mockResolvedValue(null);
    return repo;
  };

  it('/owner/start는 상점주 셸 안(OwnerLayout)이고 TabBar가 없다', () => {
    renderStoreAt('/owner/start', signedInFakes(ownerUser));
    expect(document.querySelector('.app')).not.toBeNull();
    expect(screen.queryAllByRole('link', { name: '오늘' })).toHaveLength(0);
  });

  it('/owner/store/close는 상점주 셸 안이고 TabBar가 없다', () => {
    renderStoreAt('/owner/store/close', signedInFakes(ownerUser));
    expect(document.querySelector('.app')).not.toBeNull();
    expect(screen.queryAllByRole('link', { name: '오늘' })).toHaveLength(0);
  });

  it('계정 APPROVED + 상점 없음 + /owner → 최종 O0 폼이 보인다', async () => {
    renderStoreAt('/owner', signedInFakes(ownerUser), noneRepo());
    expect(await screen.findByLabelText(/픽업 주소/)).toBeInTheDocument();
  });

  it('계정 PENDING + /owner/today → O0 승인 대기', async () => {
    renderStoreAt('/owner/today', signedInFakes({ ...ownerUser, status: 'PENDING' }), noneRepo());
    expect(await screen.findByText('승인 대기 중이에요')).toBeInTheDocument();
  });

  it('상점 ACTIVE + /owner → O1 자리 page가 보인다', async () => {
    renderStoreAt('/owner', signedInFakes(ownerUser));
    expect(await screen.findByRole('heading', { name: 'O1 오늘' })).toBeInTheDocument();
  });
});
