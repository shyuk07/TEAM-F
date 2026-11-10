import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { RouteObject } from 'react-router';
import { HomePage } from '@/pages/home';
import {
  FakeLocationProvider,
  located,
} from '../../features/offers/fakes/fakeLocationProvider.fake';
import { FakeOfferRepository } from '../../features/offers/fakes/fakeOfferRepository.fake';
import { pageOf } from '../../features/offers/fakes/offers';
import { anonymousFakes } from '../../support/authFakes';
import { renderRoutesWithOffers } from '../../support/renderWithOffers';

const routes: RouteObject[] = [{ path: '/', element: <HomePage /> }];

describe('HomePage 검색어 지우기', () => {
  it('「검색어 지우기」를 누르면 입력칸도 비워진다', async () => {
    const offers = new FakeOfferRepository();
    offers.findNearby.mockResolvedValue(pageOf([]));
    renderRoutesWithOffers(routes, {
      initialEntries: ['/'],
      fakes: anonymousFakes(),
      offerFakes: { location: new FakeLocationProvider(located), offers },
    });
    const user = userEvent.setup();
    await screen.findByText('근처에 마감 할인이 없어요');
    await user.type(screen.getByLabelText('상품명 검색'), '딸기{Enter}');
    await user.click(await screen.findByRole('button', { name: '검색어 지우기' }));
    await waitFor(() => expect(screen.getByLabelText('상품명 검색')).toHaveValue(''));
  });
});

describe('HomePage 검색 입력 포커스', () => {
  it('Enter로 검색한 뒤에도 입력칸에 포커스가 남는다', async () => {
    renderRoutesWithOffers(routes, {
      initialEntries: ['/'],
      fakes: anonymousFakes(),
      offerFakes: {
        location: new FakeLocationProvider(located),
        offers: new FakeOfferRepository(),
      },
    });
    const user = userEvent.setup();
    await screen.findByRole('link', { name: '로그인' });
    await screen.findByText('식빵 모둠 5종');
    const input = screen.getByLabelText('상품명 검색');
    await user.type(input, '빵{Enter}');
    await waitFor(() => expect(screen.getByLabelText('상품명 검색')).toHaveValue('빵'));
    expect(document.activeElement).toBe(screen.getByLabelText('상품명 검색'));
  });
});
