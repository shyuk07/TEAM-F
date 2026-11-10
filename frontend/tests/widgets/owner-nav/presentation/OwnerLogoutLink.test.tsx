import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { OwnerLogoutLink } from '@/widgets/owner-nav';
import { createAuthContainer, signedInFakes } from '../../../support/authFakes';
import { DepsProvider } from '@/shared/lib/DepsProvider';

function renderLink() {
  const fakes = signedInFakes();
  render(
    <DepsProvider container={createAuthContainer(fakes)}>
      <div className="app">
        <OwnerLogoutLink />
      </div>
    </DepsProvider>,
  );
  return { fakes };
}

describe('widgets/owner-nav OwnerLogoutLink', () => {
  it('「로그아웃」 버튼이 보인다', () => {
    renderLink();
    expect(screen.getByRole('button', { name: '로그아웃' })).toBeInTheDocument();
  });

  it('누르면 「로그아웃할까요?」 시트(alertdialog)가 열린다', async () => {
    renderLink();
    await userEvent.click(screen.getByRole('button', { name: '로그아웃' }));
    expect(await screen.findByRole('alertdialog')).toHaveTextContent('로그아웃할까요?');
  });

  it('「취소」로 닫히고 링크로 포커스가 돌아온다', async () => {
    renderLink();
    await userEvent.click(screen.getByRole('button', { name: '로그아웃' }));
    await userEvent.click(await screen.findByRole('button', { name: '취소' }));
    await waitFor(() => expect(screen.queryByRole('alertdialog')).toBeNull());
    expect(screen.getByRole('button', { name: '로그아웃' })).toHaveFocus();
  });

  it('Esc로 닫히고 링크로 포커스가 돌아온다', async () => {
    renderLink();
    await userEvent.click(screen.getByRole('button', { name: '로그아웃' }));
    await screen.findByRole('alertdialog');
    await userEvent.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('alertdialog')).toBeNull());
    expect(screen.getByRole('button', { name: '로그아웃' })).toHaveFocus();
  });

  it('「로그아웃」 확정 → auth.logout이 호출된다', async () => {
    const { fakes } = renderLink();
    await userEvent.click(screen.getByRole('button', { name: '로그아웃' }));
    // 시트 안의 「로그아웃」 버튼(링크 버튼과 이름이 같다)을 찾아 누른다
    const sheet = await screen.findByRole('alertdialog');
    const confirm = Array.from(sheet.querySelectorAll('button')).find(
      (b) => b.textContent === '로그아웃',
    );
    if (!confirm) throw new Error('확정 버튼을 못 찾았다');
    await userEvent.click(confirm);
    await waitFor(() => expect(fakes.auth.logout).toHaveBeenCalled());
  });
});
