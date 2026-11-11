import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { routes } from '@/app/router/routes';
import { anonymousFakes } from '../../support/authFakes';
import { fixNow, restoreNow } from '../../support/clock';
import { renderRoutesWithAuth } from '../../support/renderWithAuth';
import { makeNearby, makeOfferPage } from '../../features/offers/fakes/offers';

const ITEMS = [
  makeNearby({ id: 'a1', storeId: 'sa', storeName: '가게A', productName: '소금빵' }),
  makeNearby({ id: 'b1', storeId: 'sb', storeName: '가게B', productName: '크루아상' }),
  makeNearby({ id: 'a2', storeId: 'sa', storeName: '가게A', productName: '바게트' }),
];

function renderHome(path = '/') {
  const fakes = anonymousFakes();
  fakes.offers.findNearby.mockResolvedValue(makeOfferPage(ITEMS));
  return renderRoutesWithAuth(routes, { initialEntries: [path], fakes });
}

const offerLinks = () =>
  screen.queryAllByRole('link').filter((a) => a.getAttribute('href')?.startsWith('/offers/'));
const storeHeads = () =>
  screen
    .queryAllByRole('button')
    .filter((b) => b.hasAttribute('aria-expanded') && /가게[AB]/.test(b.textContent ?? ''));

describe('HomePage 가게별 보기', () => {
  beforeEach(() => fixNow());
  afterEach(() => restoreNow());

  it('「가게별」을 누르면 URL view=store, 가게 카드 2개, 상품 카드 없음', async () => {
    const { router } = renderHome();
    await screen.findByRole('link', { name: /소금빵/ });
    await userEvent.click(screen.getByRole('button', { name: '가게별' }));
    await waitFor(() =>
      expect(new URLSearchParams(router.state.location.search).get('view')).toBe('store'),
    );
    await waitFor(() => expect(storeHeads()).toHaveLength(2));
    expect(storeHeads()[0]).toHaveTextContent('가게A');
    expect(storeHeads()[0]).toHaveTextContent('할인 2개');
    expect(storeHeads()[1]).toHaveTextContent('가게B');
    expect(offerLinks()).toHaveLength(0);
  });

  it('가게를 누르면 그 가게 상품만 펼쳐진다', async () => {
    renderHome('/?view=store');
    await waitFor(() => expect(storeHeads()).toHaveLength(2));
    await userEvent.click(storeHeads()[0]!);
    await waitFor(() => expect(offerLinks()).toHaveLength(2));
    expect(offerLinks().map((a) => a.getAttribute('href'))).toEqual(['/offers/a1', '/offers/a2']);
    expect(storeHeads()[0]).toHaveAttribute('aria-expanded', 'true');
    expect(storeHeads()[1]).toHaveAttribute('aria-expanded', 'false');
  });

  it('「상품별」로 돌아오면 원래 목록(상품 카드 3개, 가게 카드 없음, view 없음)', async () => {
    const { router } = renderHome('/?view=store');
    await waitFor(() => expect(storeHeads()).toHaveLength(2));
    await userEvent.click(screen.getByRole('button', { name: '상품별' }));
    await waitFor(() => expect(offerLinks()).toHaveLength(3));
    expect(offerLinks().map((a) => a.getAttribute('href'))).toEqual([
      '/offers/a1',
      '/offers/b1',
      '/offers/a2',
    ]);
    expect(storeHeads()).toHaveLength(0);
    expect(new URLSearchParams(router.state.location.search).has('view')).toBe(false);
  });
});
