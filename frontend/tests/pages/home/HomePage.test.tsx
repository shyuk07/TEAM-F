import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { RouteObject } from 'react-router';
import { HomePage } from '@/pages/home';
import type { NearbyOfferPage } from '@/features/offers';
import { ApiError } from '@/shared/api/error';
import { deferred } from '../../features/auth/fakes/deferred';
import { customerUser } from '../../features/auth/fakes/users';
import {
  FakeLocationProvider,
  located,
  unavailable,
} from '../../features/offers/fakes/fakeLocationProvider.fake';
import { FakeOfferRepository } from '../../features/offers/fakes/fakeOfferRepository.fake';
import { manyOffers, pageOf } from '../../features/offers/fakes/offers';
import { anonymousFakes, signedInFakes, type AuthFakes } from '../../support/authFakes';
import { renderRoutesWithOffers } from '../../support/renderWithOffers';

const routes: RouteObject[] = [
  { path: '/', element: <HomePage /> },
  { path: '/login', element: <p>로그인 화면</p> },
  { path: '/signup', element: <p>가입 화면</p> },
];

type Setup = { location?: FakeLocationProvider; offers?: FakeOfferRepository; auth?: AuthFakes };

function renderHome({ location, offers, auth }: Setup = {}) {
  const offerFakes = {
    location: location ?? new FakeLocationProvider(located),
    offers: offers ?? new FakeOfferRepository(),
  };
  const result = renderRoutesWithOffers(routes, {
    initialEntries: ['/'],
    fakes: auth ?? anonymousFakes(),
    offerFakes,
  });
  return { ...result, user: userEvent.setup() };
}

const cards = () => screen.queryAllByText(/^[abp]\d? 상품 \d+$/);

function repoWith(page: NearbyOfferPage) {
  const offers = new FakeOfferRepository();
  offers.findNearby.mockResolvedValue(page);
  return offers;
}

const lastQuery = (offers: FakeOfferRepository) => offers.findNearby.mock.calls.at(-1)?.[0];

describe('HomePage (C1)', () => {
  it('위치 확인 중: Skeleton(aria-busy)과 「위치 확인 중」 칩이 있고 목록은 없다', async () => {
    const { offerFakes } = renderHome({ location: new FakeLocationProvider() });
    expect(await screen.findByText('위치 확인 중')).toBeInTheDocument();
    expect(document.querySelector('[aria-busy="true"]')).not.toBeNull();
    expect(cards()).toHaveLength(0);
    expect(offerFakes.offers.findNearby).not.toHaveBeenCalled();
  });

  it('위치 허용 + 성공: 카드 N개, 칩 「내 주변 · 3km」, 거리 표시, 마감 임박 선택', async () => {
    renderHome({ offers: repoWith(pageOf(manyOffers(3, 'p1', 0.4))) });
    await waitFor(() => expect(cards()).toHaveLength(3));
    expect(screen.getByText('내 주변 · 3km')).toBeInTheDocument();
    expect(screen.getAllByText('망원베이커리 · 0.4km')).toHaveLength(3);
    expect(screen.getByRole('button', { name: '마감 임박' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
  });

  it('위치 거부 + 성공: 카드 N개, 거리 숨김, 가까운 순 비활성, 칩 「위치 없음」', async () => {
    renderHome({
      location: new FakeLocationProvider(unavailable),
      offers: repoWith(pageOf(manyOffers(3, 'p1', null))),
    });
    await waitFor(() => expect(cards()).toHaveLength(3));
    expect(screen.queryByText(/km/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '가까운 순' })).toBeDisabled();
    expect(screen.getByText('위치 없음')).toBeInTheDocument();
  });

  it('오류: 안내 문구(role=alert)와 「다시 시도」, 누르면 재조회해 목록을 그린다', async () => {
    const offers = new FakeOfferRepository();
    offers.findNearby.mockRejectedValueOnce(new ApiError(500, 'INTERNAL_ERROR', 'x'));
    const { user } = renderHome({ offers });
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('할인 목록을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.');
    await user.click(screen.getByRole('button', { name: '다시 시도' }));
    expect(await screen.findByText('식빵 모둠 5종')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(offers.findNearby).toHaveBeenCalledTimes(2);
  });

  it('빈(검색어 없음·위치 있음): 안내와 「반경 5km로 넓히기」, 누르면 5km로 재조회하고 칩이 바뀐다', async () => {
    const offers = new FakeOfferRepository();
    offers.findNearby.mockResolvedValueOnce(pageOf([]));
    const { user } = renderHome({ offers });
    expect(await screen.findByText('근처에 마감 할인이 없어요')).toBeInTheDocument();
    expect(screen.getByText('반경을 넓히거나 저녁 시간에 다시 확인해 보세요.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '반경 5km로 넓히기' }));
    await waitFor(() => expect(lastQuery(offers)).toMatchObject({ area: { radiusKm: 5 } }));
    expect(await screen.findByText('식빵 모둠 5종')).toBeInTheDocument();
    expect(screen.getByText('내 주변 · 5km')).toBeInTheDocument();
  });

  it('빈(검색어 있음): 「검색 결과가 없어요」와 「검색어 지우기」', async () => {
    const offers = repoWith(pageOf([]));
    const { user } = renderHome({ offers });
    await screen.findByText('근처에 마감 할인이 없어요');
    await user.type(screen.getByLabelText('상품명 검색'), '빵{Enter}');
    expect(await screen.findByText('검색 결과가 없어요')).toBeInTheDocument();
    expect(screen.getByText('다른 상품명으로 검색해 보세요.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: '검색어 지우기' }));
    await waitFor(() => expect(lastQuery(offers)?.keyword).toBeUndefined());
  });

  it('빈(위치 없음): 안내만 있고 버튼이 없다', async () => {
    renderHome({ location: new FakeLocationProvider(unavailable), offers: repoWith(pageOf([])) });
    expect(await screen.findByText('근처에 마감 할인이 없어요')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '반경 5km로 넓히기' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '검색어 지우기' })).not.toBeInTheDocument();
  });

  it('더 보기: hasMore면 버튼, 누르면 2쪽이 이어 붙고 불러오는 동안 「처리 중…」·disabled', async () => {
    const offers = new FakeOfferRepository();
    offers.findNearby.mockResolvedValueOnce(pageOf(manyOffers(20, 'a'), 1, 20, 25));
    const d = deferred<NearbyOfferPage>();
    offers.findNearby.mockReturnValueOnce(d.promise);
    const { user } = renderHome({ offers });
    await waitFor(() => expect(cards()).toHaveLength(20));
    await user.click(screen.getByRole('button', { name: '더 보기' }));
    const busy = screen.getByRole('button', { name: '처리 중…' });
    expect(busy).toBeDisabled();
    expect(lastQuery(offers)).toMatchObject({ page: 2 });
    d.resolve(pageOf(manyOffers(5, 'b'), 2, 20, 25));
    await waitFor(() => expect(cards()).toHaveLength(25));
    expect(screen.queryByRole('button', { name: '더 보기' })).not.toBeInTheDocument();
  });

  it('더 보기 실패: 오류 한 줄이 나오고 목록은 유지된다', async () => {
    const offers = new FakeOfferRepository();
    offers.findNearby.mockResolvedValueOnce(pageOf(manyOffers(20, 'a'), 1, 20, 25));
    offers.findNearby.mockRejectedValueOnce(new ApiError(500, 'INTERNAL_ERROR', 'x'));
    const { user } = renderHome({ offers });
    await waitFor(() => expect(cards()).toHaveLength(20));
    await user.click(screen.getByRole('button', { name: '더 보기' }));
    expect(await screen.findByText('더 불러오지 못했어요. 다시 시도해 주세요.')).toBeVisible();
    expect(cards()).toHaveLength(20);
  });

  it('정렬 칩 「할인율」: sort=discount_rate로 재조회하고 aria-pressed가 옮겨 간다', async () => {
    const offers = new FakeOfferRepository();
    const { user } = renderHome({ offers });
    await screen.findByText('식빵 모둠 5종');
    await user.click(screen.getByRole('button', { name: '할인율' }));
    await waitFor(() => expect(lastQuery(offers)).toMatchObject({ sort: 'discount_rate' }));
    expect(screen.getByRole('button', { name: '할인율' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: '마감 임박' })).not.toHaveAttribute(
      'aria-pressed',
      'true',
    );
  });

  it('검색어 Enter: keyword로 재조회한다', async () => {
    const offers = new FakeOfferRepository();
    const { user } = renderHome({ offers });
    await screen.findByText('식빵 모둠 5종');
    await user.type(screen.getByLabelText('상품명 검색'), '빵{Enter}');
    await waitFor(() => expect(lastQuery(offers)).toMatchObject({ keyword: '빵' }));
  });

  it('위치 칩은 button이고 이름이 칩 라벨이다', async () => {
    renderHome();
    await screen.findByText('내 주변 · 3km');
    expect(screen.getByRole('button', { name: '내 주변 · 3km' })).toBeInTheDocument();
  });

  describe('위치·반경 시트 (C1a)', () => {
    async function openSheet(ctx: ReturnType<typeof renderHome>, chipName = '내 주변 · 3km') {
      const chip = await screen.findByRole('button', { name: chipName });
      await ctx.user.click(chip);
      return { chip, dialog: await screen.findByRole('dialog') };
    }

    it('칩을 누르면 dialog가 보이고 칩의 aria-expanded가 true다', async () => {
      const ctx = renderHome();
      const { chip, dialog } = await openSheet(ctx);
      expect(dialog).toBeVisible();
      expect(chip).toHaveAttribute('aria-expanded', 'true');
    });

    it('시트에서 5km를 고르면(적용 전) 저장소 호출 수와 칩 라벨이 그대로다', async () => {
      const ctx = renderHome();
      await screen.findByText('식빵 모둠 5종');
      const calls = ctx.offerFakes.offers.findNearby.mock.calls.length;
      const { dialog } = await openSheet(ctx);
      await ctx.user.click(within(dialog).getByRole('button', { name: '5km' }));
      expect(ctx.offerFakes.offers.findNearby).toHaveBeenCalledTimes(calls);
      expect(screen.getByRole('button', { name: '내 주변 · 3km' })).toBeInTheDocument();
    });

    it('「적용」 → 시트가 닫히고 area.radiusKm 5로 재조회하며 칩이 내 주변 · 5km가 된다', async () => {
      const ctx = renderHome();
      await screen.findByText('식빵 모둠 5종');
      const { dialog } = await openSheet(ctx);
      await ctx.user.click(within(dialog).getByRole('button', { name: '5km' }));
      await ctx.user.click(within(dialog).getByRole('button', { name: '적용' }));
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      await waitFor(() =>
        expect(lastQuery(ctx.offerFakes.offers)).toMatchObject({ area: { radiusKm: 5 } }),
      );
      expect(screen.getByRole('button', { name: '내 주변 · 5km' })).toBeInTheDocument();
    });

    it('Esc → 닫히고 반경 3이 유지되며 포커스가 칩으로 돌아온다', async () => {
      const ctx = renderHome();
      await screen.findByText('식빵 모둠 5종');
      const { chip, dialog } = await openSheet(ctx);
      await ctx.user.click(within(dialog).getByRole('button', { name: '10km' }));
      await ctx.user.keyboard('{Escape}');
      await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
      expect(screen.getByRole('button', { name: '내 주변 · 3km' })).toBeInTheDocument();
      expect(lastQuery(ctx.offerFakes.offers)).toMatchObject({ area: { radiusKm: 3 } });
      await waitFor(() => expect(chip).toHaveFocus());
    });

    it('「현재 위치 사용」 → 위치 provider 호출 +1, 시트는 유지된다', async () => {
      const ctx = renderHome();
      await screen.findByText('식빵 모둠 5종');
      const calls = ctx.offerFakes.location.current.mock.calls.length;
      const { dialog } = await openSheet(ctx);
      await ctx.user.click(within(dialog).getByRole('button', { name: '◎ 현재 위치 사용' }));
      expect(ctx.offerFakes.location.current).toHaveBeenCalledTimes(calls + 1);
      expect(screen.getByRole('dialog')).toBeInTheDocument();
    });

    it('위치 거부: 칩 「위치 없음」·시트 「지금: 위치 없음」, 5km를 적용해도 조회 area는 null이다', async () => {
      const ctx = renderHome({ location: new FakeLocationProvider(unavailable) });
      await screen.findByText('식빵 모둠 5종');
      const { dialog } = await openSheet(ctx, '위치 없음');
      expect(within(dialog).getByText('지금: 위치 없음')).toBeInTheDocument();
      await ctx.user.click(within(dialog).getByRole('button', { name: '5km' }));
      await ctx.user.click(within(dialog).getByRole('button', { name: '적용' }));
      await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
      expect(lastQuery(ctx.offerFakes.offers)).toMatchObject({ area: null });
    });
  });

  it('로그인 링크: anonymous면 /login으로 가는 「로그인」이 있고 state가 없다', async () => {
    const { user, router } = renderHome();
    const link = await screen.findByRole('link', { name: '로그인' });
    expect(link).toHaveAttribute('href', '/login');
    await user.click(link);
    expect(router.state.location.pathname).toBe('/login');
    expect(router.state.location.state).toBeNull();
  });

  it('로그인 링크: authenticated면 없다', async () => {
    const auth = signedInFakes(customerUser);
    renderHome({ auth });
    await screen.findByText('식빵 모둠 5종');
    await waitFor(() => expect(auth.auth.findMe).toHaveBeenCalled());
    expect(screen.queryByRole('link', { name: '로그인' })).not.toBeInTheDocument();
  });

  it('로그인 링크: 세션 확인 중(loading)이면 없다', async () => {
    const auth = signedInFakes(customerUser);
    auth.auth.findMe.mockReturnValue(deferred<typeof customerUser>().promise);
    renderHome({ auth });
    await screen.findByText('식빵 모둠 5종');
    expect(screen.queryByRole('link', { name: '로그인' })).not.toBeInTheDocument();
  });

  it('로그인 링크: 세션 오류(error)여도 목록은 그리고 링크는 없다', async () => {
    const auth = signedInFakes(customerUser);
    auth.auth.findMe.mockRejectedValue(new ApiError(500, 'INTERNAL_ERROR', 'x'));
    renderHome({ auth });
    expect(await screen.findByText('식빵 모둠 5종')).toBeInTheDocument();
    await waitFor(() => expect(auth.auth.findMe).toHaveBeenCalled());
    expect(screen.queryByRole('link', { name: '로그인' })).not.toBeInTheDocument();
  });

  it.each([
    ['anonymous', () => anonymousFakes()],
    ['authenticated', () => signedInFakes(customerUser)],
  ])('입점 신청 링크: %s에서도 /signup?role=owner로 가는 링크가 있다', async (_name, makeAuth) => {
    renderHome({ auth: makeAuth() });
    const link = await screen.findByRole('link', { name: '사장님이신가요? 입점 신청' });
    expect(link).toHaveAttribute('href', '/signup?role=owner');
  });

  it('상단 로고 「마감직전」이 있다', async () => {
    renderHome();
    expect(await screen.findByText('마감직전')).toBeInTheDocument();
  });
});
