import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { LocationSheet, type LocationSheetState } from '@/features/offers';

function fakeSheet(overrides: Partial<LocationSheetState> = {}) {
  const sheet: LocationSheetState = {
    isOpen: true,
    open: vi.fn(),
    close: vi.fn(),
    draftRadiusKm: 3,
    selectRadius: vi.fn(),
    apply: vi.fn(),
    statusLine: '지금: 현재 위치',
    canUseCurrent: true,
    refreshLocation: vi.fn(),
    ...overrides,
  };
  return sheet;
}

function setup(overrides: Partial<LocationSheetState> = {}) {
  const sheet = fakeSheet(overrides);
  render(<LocationSheet sheet={sheet} />);
  return { sheet, user: userEvent.setup(), dialog: screen.getByRole('dialog') };
}

const chipsOf = (dialog: HTMLElement) =>
  within(within(dialog).getByRole('group', { name: '반경' })).getAllByRole('button');

describe('LocationSheet', () => {
  it('제목이 있고 dialog·aria-modal·aria-labelledby가 제목을 가리킨다', () => {
    const { dialog } = setup();
    const title = screen.getByText('어디서 찾을까요?');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
    expect(title.id).not.toBe('');
    expect(dialog).toHaveAttribute('aria-labelledby', title.id);
  });

  it('버튼 「◎ 현재 위치 사용」·「적용」, 라벨 「반경」, 안내 문구가 있다', () => {
    const { dialog } = setup();
    expect(within(dialog).getByRole('button', { name: '◎ 현재 위치 사용' })).toBeInTheDocument();
    expect(within(dialog).getByRole('button', { name: '적용' })).toBeInTheDocument();
    expect(within(dialog).getByText('반경')).toBeInTheDocument();
    expect(
      within(dialog).getByText('위치를 허용하지 않으면 거리 없이 전체 할인을 보여 줘요.'),
    ).toBeInTheDocument();
  });

  it('반경 칩 4개가 1km·3km·5km·10km 순서다', () => {
    const { dialog } = setup();
    expect(chipsOf(dialog).map((b) => b.textContent)).toEqual(['1km', '3km', '5km', '10km']);
  });

  it('draftRadiusKm 칩만 aria-pressed="true"이고 on이다', () => {
    const { dialog } = setup({ draftRadiusKm: 5 });
    for (const chip of chipsOf(dialog)) {
      const selected = chip.textContent === '5km';
      expect(chip).toHaveAttribute('aria-pressed', selected ? 'true' : 'false');
      if (selected) expect(chip).toHaveClass('on');
      else expect(chip).not.toHaveClass('on');
    }
  });

  it('칩을 누르면 selectRadius(5)', async () => {
    const { sheet, user, dialog } = setup();
    await user.click(within(dialog).getByRole('button', { name: '5km' }));
    expect(sheet.selectRadius).toHaveBeenCalledWith(5);
  });

  it('statusLine이 보인다', () => {
    const { dialog } = setup();
    expect(within(dialog).getByText('지금: 현재 위치')).toBeVisible();
  });

  it('「◎ 현재 위치 사용」을 누르면 refreshLocation', async () => {
    const { sheet, user, dialog } = setup();
    await user.click(within(dialog).getByRole('button', { name: '◎ 현재 위치 사용' }));
    expect(sheet.refreshLocation).toHaveBeenCalledTimes(1);
  });

  it('canUseCurrent false → aria-disabled="true"이고 눌러도 refreshLocation 0회', async () => {
    const { sheet, user, dialog } = setup({ canUseCurrent: false });
    const button = within(dialog).getByRole('button', { name: '◎ 현재 위치 사용' });
    expect(button).toHaveAttribute('aria-disabled', 'true');
    await user.click(button);
    expect(sheet.refreshLocation).not.toHaveBeenCalled();
  });

  it('「적용」을 누르면 apply', async () => {
    const { sheet, user, dialog } = setup();
    await user.click(within(dialog).getByRole('button', { name: '적용' }));
    expect(sheet.apply).toHaveBeenCalledTimes(1);
  });

  it('Esc → close', async () => {
    const { sheet, user } = setup();
    await user.keyboard('{Escape}');
    expect(sheet.close).toHaveBeenCalledTimes(1);
  });

  it('딤 클릭 → close', async () => {
    const { sheet, user, dialog } = setup();
    const dim = dialog.parentElement as HTMLElement;
    expect(dim).toHaveClass('dim');
    await user.click(dim);
    expect(sheet.close).toHaveBeenCalledTimes(1);
  });

  it('시트 안쪽 클릭은 close가 아니다', async () => {
    const { sheet, user, dialog } = setup();
    await user.click(within(dialog).getByText('어디서 찾을까요?'));
    expect(sheet.close).not.toHaveBeenCalled();
  });

  it('열릴 때 첫 포커스가 「◎ 현재 위치 사용」이다', async () => {
    const { dialog } = setup();
    await waitFor(() =>
      expect(within(dialog).getByRole('button', { name: '◎ 현재 위치 사용' })).toHaveFocus(),
    );
  });

  it('「취소」 버튼이 없다', () => {
    const { dialog } = setup();
    expect(within(dialog).queryByRole('button', { name: '취소' })).not.toBeInTheDocument();
  });
});
