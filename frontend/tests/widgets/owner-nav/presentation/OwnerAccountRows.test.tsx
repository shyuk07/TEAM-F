import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { OwnerAccountRows } from '@/widgets/owner-nav';
import { ownerUser } from '../../../features/auth/fakes/users';
import { signedInFakes } from '../../../support/authFakes';
import { renderWithOwnerStore } from '../../../support/renderWithOwnerStore';

function renderRows() {
  return renderWithOwnerStore(<OwnerAccountRows />, {
    initialEntries: ['/owner/store?x=1'],
    fakes: signedInFakes(ownerUser),
  });
}

describe('widgets/owner-nav OwnerAccountRows (products.md §5.1, D-19)', () => {
  it('「계정」 라벨과 「비밀번호 변경」 링크·「로그아웃」 행이 있다', () => {
    renderRows();
    expect(screen.getByText('계정', { selector: '.lbl' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /^비밀번호 변경/ })).toHaveAttribute(
      'href',
      '/account/password',
    );
    expect(screen.getByRole('button', { name: /^로그아웃/ })).toBeInTheDocument();
  });

  it('「비밀번호 변경」을 누르면 현재 경로를 state.from으로 넘긴다', async () => {
    const { router } = renderRows();
    await userEvent.click(screen.getByRole('link', { name: /^비밀번호 변경/ }));
    await waitFor(() => expect(router.state.location.pathname).toBe('/account/password'));
    expect(router.state.location.state).toEqual({ from: '/owner/store?x=1' });
  });

  it('「로그아웃」 행을 누르면 확인 시트가 열린다', async () => {
    renderRows();
    await userEvent.click(screen.getByRole('button', { name: /^로그아웃/ }));
    expect(await screen.findByRole('alertdialog')).toBeInTheDocument();
  });

  it('계정 행은 PC에서 숨기는 .mob 요소 안에 있다', () => {
    renderRows();
    const wrapper = screen.getByText('계정', { selector: '.lbl' }).closest('.mob');
    expect(wrapper).not.toBeNull();
    expect(wrapper).toContainElement(screen.getByRole('link', { name: /^비밀번호 변경/ }));
    expect(wrapper).toContainElement(screen.getByRole('button', { name: /^로그아웃/ }));
  });

  it('.mob 요소에 인라인 display가 없다 (인라인 display가 .mob{display:none}을 덮어 PC에서 보이던 결함 회귀 방지)', () => {
    renderRows();
    const mob = screen.getByText('계정', { selector: '.lbl' }).closest<HTMLElement>('.mob');
    expect(mob).not.toBeNull();
    expect(mob?.style.display).toBe('');
    expect(mob?.getAttribute('style')).toBeNull();
  });
});

// app-shell.md §11.9: 오버레이는 .app의 직계 .body를 숨기고 .dim으로 시트를 띄운다.
describe('widgets/owner-nav OwnerAccountRows 오버레이 (app-shell.md §11.9)', () => {
  function renderFrame() {
    return renderWithOwnerStore(
      <div className="app">
        <div className="bar">매장</div>
        <div className="body">
          <input aria-label="메모" />
          <OwnerAccountRows />
        </div>
        <div className="tabs">탭</div>
      </div>,
      { initialEntries: ['/owner/store'], fakes: signedInFakes(ownerUser) },
    );
  }
  const body = (c: HTMLElement) => c.querySelector<HTMLElement>('.app > .body') as HTMLElement;

  it('「로그아웃」을 누르면 .dim 안에 확인 시트가 뜨고 .body는 hidden이다', async () => {
    const { container } = renderFrame();
    await userEvent.click(screen.getByRole('button', { name: /^로그아웃/ }));
    const sheet = await screen.findByRole('alertdialog');
    expect(sheet.closest('.dim')).not.toBeNull();
    expect(body(container).hidden).toBe(true);
  });

  it('시트를 닫으면 .body가 복원되고 같은 행 버튼으로 포커스가 돌아오며 상태가 유지된다', async () => {
    const { container } = renderFrame();
    await userEvent.type(screen.getByLabelText('메모'), '유지');
    const row = screen.getByRole('button', { name: /^로그아웃/ });
    await userEvent.click(row);
    await screen.findByRole('alertdialog');
    await userEvent.click(screen.getByRole('button', { name: '취소' }));
    await waitFor(() => expect(screen.queryByRole('alertdialog')).toBeNull());
    expect(body(container).hidden).toBe(false);
    expect(container.querySelector('.dim')).toBeNull();
    expect(screen.getByRole('button', { name: /^로그아웃/ })).toHaveFocus();
    expect(screen.getByLabelText('메모')).toHaveValue('유지');
  });
});
