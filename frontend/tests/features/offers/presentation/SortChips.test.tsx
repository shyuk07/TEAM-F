import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SortChips } from '@/features/offers';

describe('SortChips', () => {
  it('칩 4개가 순서대로 있다', () => {
    render(<SortChips sort="sales_end" hasLocation onSelect={vi.fn()} />);
    expect(screen.getAllByRole('button').map((b) => b.textContent)).toEqual([
      '마감 임박',
      '가까운 순',
      '할인율',
      '낮은 가격',
    ]);
  });

  it('선택된 칩에만 aria-pressed="true"', () => {
    render(<SortChips sort="discount_rate" hasLocation onSelect={vi.fn()} />);
    expect(screen.getByRole('button', { name: '할인율' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('button', { name: '마감 임박' })).not.toHaveAttribute(
      'aria-pressed',
      'true',
    );
  });

  it('위치가 있으면 가까운 순이 활성이고 누르면 onSelect(distance)', async () => {
    const onSelect = vi.fn();
    render(<SortChips sort="sales_end" hasLocation onSelect={onSelect} />);
    const chip = screen.getByRole('button', { name: '가까운 순' });
    expect(chip).toBeEnabled();
    await userEvent.click(chip);
    expect(onSelect).toHaveBeenCalledWith('distance');
  });

  it('위치가 없으면 가까운 순이 disabled이고 눌러도 onSelect가 불리지 않는다', async () => {
    const onSelect = vi.fn();
    render(<SortChips sort="sales_end" hasLocation={false} onSelect={onSelect} />);
    const chip = screen.getByRole('button', { name: '가까운 순' });
    expect(chip).toBeDisabled();
    expect(chip).toHaveAttribute('aria-disabled', 'true');
    await userEvent.click(chip);
    expect(onSelect).not.toHaveBeenCalled();
  });

  it('다른 칩을 누르면 그 키로 onSelect', async () => {
    const onSelect = vi.fn();
    render(<SortChips sort="sales_end" hasLocation onSelect={onSelect} />);
    await userEvent.click(screen.getByRole('button', { name: '할인율' }));
    await userEvent.click(screen.getByRole('button', { name: '낮은 가격' }));
    expect(onSelect.mock.calls).toEqual([['discount_rate'], ['price']]);
  });
});
