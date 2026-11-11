import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router';
import { vi } from 'vitest';
import { StoreGroupCard, type StoreGroup } from '@/features/offers';
import { NOW, at } from '../../../support/clock';
import { makeNearby } from '../fakes/offers';

function group(distanceKm: number | null): StoreGroup {
  return {
    storeId: 's1',
    storeName: '망원베이커리',
    distanceKm,
    earliestSalesEnd: at(10, 18, 0),
    offers: [
      makeNearby({ id: 'o1', productName: '소금빵 세트' }, distanceKm),
      makeNearby({ id: 'o2', productName: '크루아상' }, distanceKm),
    ],
  };
}

function renderCard(g: StoreGroup, expanded: boolean, onToggle = vi.fn()) {
  render(
    <MemoryRouter>
      <StoreGroupCard group={g} now={NOW} expanded={expanded} onToggle={onToggle} />
    </MemoryRouter>,
  );
  return onToggle;
}

describe('StoreGroupCard', () => {
  it('접힘: 머리 버튼(aria-expanded false)에 가게명·「할인 2개」·거리·「가장 빠른 마감」, 상품 카드 없음', () => {
    renderCard(group(0.42), false);
    const head = screen.getByRole('button', { name: /망원베이커리/ });
    expect(head).toHaveAttribute('aria-expanded', 'false');
    expect(head).toHaveTextContent('할인 2개');
    expect(head).toHaveTextContent('0.4km');
    expect(head).toHaveTextContent('가장 빠른 마감');
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
    expect(screen.queryByText('소금빵 세트')).not.toBeInTheDocument();
  });

  it('거리가 null이면 거리 표시 없음', () => {
    renderCard(group(null), false);
    const head = screen.getByRole('button', { name: /망원베이커리/ });
    expect(head).toHaveTextContent('할인 2개');
    expect(head).not.toHaveTextContent('km');
  });

  it('펼침: aria-expanded true, 그 가게 상품 카드(링크)들', () => {
    renderCard(group(0.42), true);
    expect(screen.getByRole('button', { name: /망원베이커리/ })).toHaveAttribute(
      'aria-expanded',
      'true',
    );
    expect(screen.getByRole('link', { name: /소금빵 세트/ })).toHaveAttribute('href', '/offers/o1');
    expect(screen.getByRole('link', { name: /크루아상/ })).toHaveAttribute('href', '/offers/o2');
  });

  it('머리를 누르면 onToggle', async () => {
    const onToggle = renderCard(group(0.42), false);
    await userEvent.click(screen.getByRole('button', { name: /망원베이커리/ }));
    expect(onToggle).toHaveBeenCalledTimes(1);
  });
});
