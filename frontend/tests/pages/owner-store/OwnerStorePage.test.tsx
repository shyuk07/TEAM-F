import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { OwnerStorePage } from '@/pages/owner-store';
import { FakeStoreRepository } from '../../entities/store/fakes/fakeStoreRepository.fake';
import { suspendedStore } from '../../entities/store/fakes/stores';
import { ownerUser } from '../../features/auth/fakes/users';
import { signedInFakes } from '../../support/authFakes';
import { renderWithOwnerStore } from '../../support/renderWithOwnerStore';

function renderPage(repo = new FakeStoreRepository()) {
  return renderWithOwnerStore(<OwnerStorePage />, {
    initialEntries: ['/owner/store'],
    fakes: signedInFakes(ownerUser),
    repo,
  });
}

describe('pages/owner-store OwnerStorePage', () => {
  it('상점 이름·주소·태그 「영업 중」을 그린다', async () => {
    renderPage();
    expect(await screen.findByText('서울시 마포구 망원로 10')).toBeInTheDocument();
    expect(screen.getAllByText('망원베이커리').length).toBeGreaterThan(0);
    expect(screen.getByText('영업 중')).toHaveClass('tag', 'ok');
  });

  // §5.1 결함 1: .box(grid)의 직접 자식이면 칩이 열 폭으로 늘어난다 → 일반 div 한 겹으로 감싼다
  it('「영업 중」 태그의 부모는 일반 div이고 그 부모가 .box다', async () => {
    renderPage();
    const tag = await screen.findByText('영업 중');
    const wrapper = tag.parentElement;
    expect(wrapper).not.toBeNull();
    expect(wrapper?.classList.contains('box')).toBe(false);
    expect(wrapper?.tagName).toBe('DIV');
    expect(wrapper?.parentElement).toHaveClass('box');
  });

  // §5.1 결함 2: 오른쪽 열에 간격(토큰만)을 주고, 폐점 링크는 div로 감싸 열 폭으로 늘어나지 않게 한다
  it('「상점 폐점」 링크의 부모 div는 오른쪽 열의 직접 자식이고 열은 grid + gap var(--s3)', async () => {
    renderPage();
    const link = await screen.findByRole('link', { name: '상점 폐점' });
    const wrapper = link.parentElement;
    expect(wrapper?.tagName).toBe('DIV');
    const column = wrapper?.parentElement as HTMLElement;
    expect(column).not.toBeNull();
    expect(column.parentElement).toHaveClass('split');
    expect(column.style.display).toBe('grid');
    const style = column.getAttribute('style') ?? '';
    expect(style).toContain('var(--s3)');
    expect(style).not.toMatch(/#|rgb|\dpx/);
  });

  it('정지 상점은 태그 「상점 정지」', async () => {
    const repo = new FakeStoreRepository();
    repo.findMine.mockResolvedValue(suspendedStore);
    renderPage(repo);
    expect(await screen.findByText('상점 정지')).toBeInTheDocument();
  });

  it('상품 목록을 useOwnerStore().id로 불러오고 개수를 보여 준다', async () => {
    const { products } = renderPage();
    expect(await screen.findByText('상품 2개')).toBeInTheDocument();
    expect(products.findByStore.mock.calls[0][0]).toBe('st-1');
  });

  it('「상점 폐점」 링크는 /owner/store/close로 간다', async () => {
    renderPage();
    expect(await screen.findByRole('link', { name: '상점 폐점' })).toHaveAttribute(
      'href',
      '/owner/store/close',
    );
  });

  it('「계정」 라벨 아래 「비밀번호 변경」 링크와 「로그아웃」 버튼이 있다', async () => {
    renderPage();
    await screen.findByText('상품 2개');
    expect(screen.getByText('계정', { selector: '.lbl' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /^비밀번호 변경/ })).toHaveAttribute(
      'href',
      '/account/password',
    );
    expect(screen.getByRole('button', { name: /^로그아웃/ })).toBeInTheDocument();
  });

  it('「로그아웃」 버튼을 누르면 로그아웃 확인 시트가 열린다', async () => {
    renderPage();
    await screen.findByText('상품 2개');
    await userEvent.click(screen.getByRole('button', { name: /^로그아웃/ }));
    expect(await screen.findByRole('alertdialog')).toBeInTheDocument();
  });

  it('상품 행을 누르면 /owner/products/p1로 이동한다', async () => {
    const { router } = renderPage();
    await userEvent.click(await screen.findByRole('link', { name: /식빵 모둠 5종/ }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/owner/products/p1'));
  });

  it('「+ 상품 등록」을 누르면 /owner/products/new로 이동한다', async () => {
    const { router } = renderPage();
    await userEvent.click(await screen.findByRole('link', { name: '+ 상품 등록' }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/owner/products/new'));
  });
});
