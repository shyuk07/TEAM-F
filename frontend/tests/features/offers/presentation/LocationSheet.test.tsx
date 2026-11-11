import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { LocationSheet } from '@/features/offers';

describe('LocationSheet onSelectRadius', () => {
  it('반경 칩을 누르면 onSelectRadius(그 반경)이 호출되고 칩이 선택되며 onApply는 호출되지 않는다', async () => {
    const onSelectRadius = vi.fn();
    const onApply = vi.fn();
    render(
      <LocationSheet
        hasLocation
        locating={false}
        radiusKm={3}
        onUseCurrentLocation={vi.fn()}
        onApply={onApply}
        onSelectRadius={onSelectRadius}
      />,
    );
    await userEvent.click(screen.getByRole('button', { name: '10km' }));
    expect(onSelectRadius).toHaveBeenCalledTimes(1);
    expect(onSelectRadius).toHaveBeenCalledWith(10);
    expect(screen.getByRole('button', { name: '10km' })).toHaveAttribute('aria-pressed', 'true');
    expect(onApply).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole('button', { name: '1km' }));
    expect(onSelectRadius).toHaveBeenLastCalledWith(1);
  });
});
