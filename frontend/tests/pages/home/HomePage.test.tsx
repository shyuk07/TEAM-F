import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { routes } from '@/app/router/routes';
import type { User } from '@/features/auth';
import type { OfferPage } from '@/features/offers';
import { ApiError } from '@/shared/api/error';
import { anonymousFakes, signedInFakes, type AuthFakes } from '../../support/authFakes';
import { fixNow, restoreNow } from '../../support/clock';
import { renderRoutesWithAuth } from '../../support/renderWithAuth';
import { deferred } from '../../features/auth/fakes/deferred';
import { customerUser } from '../../features/auth/fakes/users';
import { MANGWON } from '../../features/offers/fakes/fakeLocationProvider.fake';
import { makeNearby, makeNearbyList, makeOfferPage } from '../../features/offers/fakes/offers';

type Opts = { fakes?: AuthFakes; path?: string; located?: boolean; page?: OfferPage };

function renderHome(opts: Opts = {}) {
  const fakes = opts.fakes ?? anonymousFakes();
  if (opts.located) fakes.location.current.mockResolvedValue(MANGWON);
  const distance = opts.located ? 0.42 : null;
  fakes.offers.findNearby.mockResolvedValue(opts.page ?? makeOfferPage([makeNearby({}, distance)]));
  return renderRoutesWithAuth(routes, { initialEntries: [opts.path ?? '/'], fakes });
}

const lastQuery = (fakes: AuthFakes) => fakes.offers.findNearby.mock.calls.at(-1)?.[0];
const card = () => screen.findByRole('link', { name: /소금빵 세트/ });
const offerLinks = () =>
  screen.queryAllByRole('link').filter((a) => a.getAttribute('href')?.startsWith('/offers/'));

describe('HomePage (C1·C1a)', () => {
  beforeEach(() => fixNow());
  afterEach(() => restoreNow());

  it('로고 heading 「마감직전」과 탭 바 「홈」 현재', async () => {
    renderHome();
    expect(await screen.findByRole('heading', { level: 1, name: '마감직전' })).toBeInTheDocument();
    const nav = screen.getByRole('navigation', { name: '고객 메뉴' });
    expect(within(nav).getByRole('link', { name: '홈' })).toHaveAttribute('aria-current', 'page');
  });

  it('위치 거부: 칩 「전체 지역」, 카드에 거리 없음, 「가까운 순」 비활성이고 눌러도 요청이 바뀌지 않는다', async () => {
    const { fakes, router } = renderHome();
    const link = await card();
    expect(screen.getByRole('button', { name: '전체 지역' })).toBeInTheDocument();
    expect(link).toHaveTextContent('망원베이커리');
    expect(link).not.toHaveTextContent('망원베이커리 ·');
    const near = screen.getByRole('button', { name: '가까운 순' });
    expect(near).toHaveAttribute('aria-disabled', 'true');
    const calls = fakes.offers.findNearby.mock.calls.length;
    await userEvent.click(near);
    expect(fakes.offers.findNearby.mock.calls.length).toBe(calls);
    expect(router.state.location.search).toBe('');
    expect(lastQuery(fakes)).toMatchObject({ location: null, sort: 'sales_end' });
  });

  it('위치 허용: 칩 「현재 위치 · 3km」, 카드에 「망원베이커리 · 0.4km」', async () => {
    const { fakes } = renderHome({ located: true });
    const link = await card();
    expect(screen.getByRole('button', { name: '현재 위치 · 3km' })).toBeInTheDocument();
    expect(link).toHaveTextContent('망원베이커리 · 0.4km');
    expect(lastQuery(fakes)).toMatchObject({ location: MANGWON, radiusKm: 3 });
    expect(screen.getByRole('button', { name: '가까운 순' })).not.toHaveAttribute(
      'aria-disabled',
      'true',
    );
  });

  it('카드: 할인가·정가(취소선)·할인율·픽업·판매 마감 카운트다운·남은 수량', async () => {
    renderHome();
    const link = await card();
    expect(within(link).getByText('6,000원')).toBeInTheDocument();
    const original = within(link).getByText('12,000');
    expect(original.tagName).toBe('S');
    expect(within(link).getByText('50%')).toBeInTheDocument();
    expect(link).toHaveTextContent('픽업 오늘 18:00–20:00');
    expect(within(link).getByText('판매 마감 42분 전')).toBeInTheDocument();
    expect(within(link).getByText('남은 3개')).toBeInTheDocument();
  });

  it('품절 카드: 「품절」 태그, 카운트다운·남은 수량 없음', async () => {
    renderHome({ page: makeOfferPage([makeNearby({ remainingStock: 0, isSoldOut: true })]) });
    const link = await card();
    expect(within(link).getByText('품절')).toBeInTheDocument();
    expect(link).not.toHaveTextContent('판매 마감');
    expect(link).not.toHaveTextContent('남은');
  });

  it('카드를 누르면 /offers/<id>의 C2 자리 page', async () => {
    const { router } = renderHome();
    await userEvent.click(await card());
    await waitFor(() => expect(router.state.location.pathname).toBe('/offers/o1'));
    expect(await screen.findByRole('heading', { name: 'C2 할인 상세' })).toBeInTheDocument();
  });

  it('정렬 「할인율」: URL ?sort=discount_rate, 요청 sort discount_rate, 칩 aria-pressed', async () => {
    const { fakes, router } = renderHome();
    await card();
    expect(screen.getByRole('button', { name: '마감 임박' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    await userEvent.click(screen.getByRole('button', { name: '할인율' }));
    await waitFor(() => expect(router.state.location.search).toBe('?sort=discount_rate'));
    await waitFor(() => expect(lastQuery(fakes)).toMatchObject({ sort: 'discount_rate' }));
    expect(screen.getByRole('button', { name: '할인율' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: '마감 임박' })).toHaveAttribute(
      'aria-pressed',
      'false',
    );
  });

  it('검색어 입력 + Enter: 요청 keyword 「빵」, URL ?q=빵', async () => {
    const { fakes, router } = renderHome();
    await card();
    const box = screen.getByRole('searchbox', { name: '상품명 검색' });
    expect(box).toHaveAttribute('maxLength', '100');
    await userEvent.type(box, '빵{Enter}');
    await waitFor(() => expect(lastQuery(fakes)).toMatchObject({ keyword: '빵', page: 1 }));
    expect(new URLSearchParams(router.state.location.search).get('q')).toBe('빵');
  });

  it('로딩은 뼈대 카드 3개와 aria-busy, 실패는 임시 문구와 「다시 시도」로 다시 요청', async () => {
    const fakes = anonymousFakes();
    const first = deferred<OfferPage>();
    fakes.offers.findNearby.mockReturnValueOnce(first.promise);
    renderRoutesWithAuth(routes, { initialEntries: ['/'], fakes });
    await waitFor(() => expect(document.querySelector('[aria-busy="true"]')).not.toBeNull());
    await waitFor(() =>
      expect(document.querySelectorAll('[aria-busy="true"] .card')).toHaveLength(3),
    );
    first.reject(new ApiError(0, 'NETWORK_ERROR', '서버 문구'));
    expect(await screen.findByRole('alert')).toHaveTextContent(
      '불러오지 못했어요. 잠시 후 다시 시도해 주세요.',
    );
    expect(screen.queryByText('서버 문구')).not.toBeInTheDocument();
    const calls = fakes.offers.findNearby.mock.calls.length;
    fakes.offers.findNearby.mockResolvedValue(makeOfferPage([makeNearby()]));
    await userEvent.click(screen.getByRole('button', { name: '다시 시도' }));
    await card();
    expect(fakes.offers.findNearby.mock.calls.length).toBe(calls + 1);
  });

  it('빈 결과: 위치가 있으면 「반경 5km로 넓히기」로 반경 5 요청, 위치가 없으면 버튼 없음', async () => {
    const { fakes, unmount } = renderHome({ located: true, page: makeOfferPage([]) });
    expect(await screen.findByText('근처에 마감 할인이 없어요')).toBeInTheDocument();
    expect(screen.getByText('반경을 넓히거나 저녁 시간에 다시 확인해 보세요.')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: '반경 5km로 넓히기' }));
    await waitFor(() => expect(lastQuery(fakes)).toMatchObject({ radiusKm: 5 }));
    unmount();

    renderHome({ page: makeOfferPage([]) });
    expect(await screen.findByText('근처에 마감 할인이 없어요')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /넓히기/ })).not.toBeInTheDocument();
  });

  it('total 25면 「더 보기」로 2페이지를 받아 카드 25개', async () => {
    const fakes = anonymousFakes();
    fakes.offers.findNearby.mockResolvedValueOnce(makeOfferPage(makeNearbyList(20), { total: 25 }));
    fakes.offers.findNearby.mockResolvedValueOnce(
      makeOfferPage(makeNearbyList(5, 21), { page: 2, total: 25 }),
    );
    renderRoutesWithAuth(routes, { initialEntries: ['/'], fakes });
    await waitFor(() => expect(offerLinks()).toHaveLength(20));
    await userEvent.click(screen.getByRole('button', { name: '더 보기' }));
    await waitFor(() => expect(offerLinks()).toHaveLength(25));
    expect(lastQuery(fakes)).toMatchObject({ page: 2 });
    expect(screen.queryByRole('button', { name: '더 보기' })).not.toBeInTheDocument();
  });

  it('비로그인은 상단 「로그인」(from:/)과 「사장님이신가요? 입점 신청」, 고객 로그인은 둘 다 없다', async () => {
    const { router, unmount } = renderHome();
    await card();
    const apply = screen.getByRole('link', { name: '사장님이신가요? 입점 신청' });
    expect(apply).toHaveAttribute('href', '/signup?role=owner');
    const login = screen.getByRole('link', { name: '로그인' });
    expect(login).toHaveAttribute('href', '/login');
    await userEvent.click(login);
    await waitFor(() => expect(router.state.location.pathname).toBe('/login'));
    expect(router.state.location.state).toEqual({ from: '/' });
    unmount();

    renderHome({ fakes: signedInFakes(customerUser) });
    await card();
    expect(screen.queryByRole('link', { name: '로그인' })).not.toBeInTheDocument();
    expect(
      screen.queryByRole('link', { name: '사장님이신가요? 입점 신청' }),
    ).not.toBeInTheDocument();
  });

  it('세션 확인 중(loading)에는 「로그인」도 「사장님이신가요? 입점 신청」도 없다(D-18)', async () => {
    const fakes = signedInFakes(customerUser);
    fakes.auth.findMe.mockReturnValue(deferred<User>().promise);
    renderHome({ fakes });
    expect(await screen.findByRole('heading', { level: 1, name: '마감직전' })).toBeInTheDocument();
    await card();
    expect(screen.queryByRole('link', { name: '로그인' })).not.toBeInTheDocument();
    expect(
      screen.queryByRole('link', { name: '사장님이신가요? 입점 신청' }),
    ).not.toBeInTheDocument();
  });

  it('C1a: 위치 칩을 누르면 .dim 안 시트가 열리고 목록 대신 보이며 첫 포커스는 「◎ 현재 위치 사용」', async () => {
    renderHome({ located: true });
    await card();
    const chip = screen.getByRole('button', { name: '현재 위치 · 3km' });
    expect(chip).toHaveAttribute('aria-expanded', 'false');
    await userEvent.click(chip);
    const dialog = await screen.findByRole('dialog', { name: '어디서 찾을까요?' });
    expect(dialog.closest('.dim')).not.toBeNull();
    expect(chip).toHaveAttribute('aria-expanded', 'true');
    const use = within(dialog).getByRole('button', { name: '◎ 현재 위치 사용' });
    await waitFor(() => expect(use).toHaveFocus());
    expect(within(dialog).getByText('지금: 현재 위치')).toBeInTheDocument();
    for (const r of ['1km', '3km', '5km', '10km']) {
      expect(within(dialog).getByRole('button', { name: r })).toBeInTheDocument();
    }
    expect(within(dialog).getByRole('button', { name: '3km' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(
      within(dialog).getByText('위치를 허용하지 않으면 거리 없이 전체 할인을 보여 줘요.'),
    ).toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: '적용' })).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /소금빵 세트/ })).not.toBeInTheDocument();
    expect(screen.queryByRole('searchbox')).not.toBeInTheDocument();
  });

  it('C1a: 「10km」 → 「적용」이면 닫히고 URL ?radius=10, 요청 반경 10, 칩 「현재 위치 · 10km」', async () => {
    const { fakes, router } = renderHome({ located: true });
    await card();
    await userEvent.click(screen.getByRole('button', { name: '현재 위치 · 3km' }));
    const dialog = await screen.findByRole('dialog', { name: '어디서 찾을까요?' });
    await userEvent.click(within(dialog).getByRole('button', { name: '10km' }));
    await userEvent.click(within(dialog).getByRole('button', { name: '적용' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    await waitFor(() => expect(router.state.location.search).toBe('?radius=10'));
    await waitFor(() => expect(lastQuery(fakes)).toMatchObject({ radiusKm: 10 }));
    expect(screen.getByRole('button', { name: '현재 위치 · 10km' })).toBeInTheDocument();
  });

  it('C1a: Escape는 적용 없이 닫고 포커스를 위치 칩으로 돌린다', async () => {
    const { fakes, router } = renderHome({ located: true });
    await card();
    const calls = fakes.offers.findNearby.mock.calls.length;
    await userEvent.click(screen.getByRole('button', { name: '현재 위치 · 3km' }));
    const dialog = await screen.findByRole('dialog', { name: '어디서 찾을까요?' });
    await userEvent.click(within(dialog).getByRole('button', { name: '5km' }));
    await userEvent.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    const chip = screen.getByRole('button', { name: '현재 위치 · 3km' });
    await waitFor(() => expect(chip).toHaveFocus());
    expect(router.state.location.search).toBe('');
    expect(fakes.offers.findNearby.mock.calls.length).toBe(calls);
  });
});
