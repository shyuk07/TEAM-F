import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { LocationChip } from '@/features/offers';

describe('LocationChip', () => {
  it('역할 button, 이름은 라벨', () => {
    render(<LocationChip label="내 주변 · 3km" open={false} onClick={() => {}} />);
    expect(screen.getByRole('button', { name: '내 주변 · 3km' })).toBeInTheDocument();
  });

  it('클릭 → onClick 1회', async () => {
    const onClick = vi.fn();
    render(<LocationChip label="내 주변 · 3km" open={false} onClick={onClick} />);
    await userEvent.setup().click(screen.getByRole('button', { name: '내 주변 · 3km' }));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('open이면 chip on 클래스와 aria-expanded="true"', () => {
    render(<LocationChip label="내 주변 · 3km" open onClick={() => {}} />);
    const chip = screen.getByRole('button', { name: '내 주변 · 3km' });
    expect(chip).toHaveClass('chip', 'on');
    expect(chip).toHaveAttribute('aria-expanded', 'true');
  });

  it('닫히면 aria-expanded="false"이고 on이 없다', () => {
    render(<LocationChip label="내 주변 · 3km" open={false} onClick={() => {}} />);
    const chip = screen.getByRole('button', { name: '내 주변 · 3km' });
    expect(chip).toHaveAttribute('aria-expanded', 'false');
    expect(chip).not.toHaveClass('on');
  });

  it('aria-haspopup="dialog"', () => {
    render(<LocationChip label="내 주변 · 3km" open={false} onClick={() => {}} />);
    expect(screen.getByRole('button', { name: '내 주변 · 3km' })).toHaveAttribute(
      'aria-haspopup',
      'dialog',
    );
  });
});
