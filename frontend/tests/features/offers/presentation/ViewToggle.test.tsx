import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { ViewToggle } from '@/features/offers';

describe('ViewToggle', () => {
  it('칩 2개, 현재 값(offer)만 aria-pressed true, 「가게별」을 누르면 onChange(store)', async () => {
    const onChange = vi.fn();
    render(<ViewToggle value="offer" onChange={onChange} />);
    const byOffer = screen.getByRole('button', { name: '상품별' });
    const byStore = screen.getByRole('button', { name: '가게별' });
    expect(screen.getAllByRole('button')).toHaveLength(2);
    expect(byOffer).toHaveAttribute('aria-pressed', 'true');
    expect(byStore).toHaveAttribute('aria-pressed', 'false');
    await userEvent.click(byStore);
    expect(onChange).toHaveBeenCalledWith('store');
  });

  it('값이 store면 「가게별」이 pressed, 「상품별」을 누르면 onChange(offer)', async () => {
    const onChange = vi.fn();
    render(<ViewToggle value="store" onChange={onChange} />);
    expect(screen.getByRole('button', { name: '가게별' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: '상품별' })).toHaveAttribute('aria-pressed', 'false');
    await userEvent.click(screen.getByRole('button', { name: '상품별' }));
    expect(onChange).toHaveBeenCalledWith('offer');
  });
});
