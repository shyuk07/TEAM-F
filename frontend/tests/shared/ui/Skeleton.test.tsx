import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Skeleton } from '@/shared/ui';

describe('shared/ui Skeleton', () => {
  it('.card 안에 .sk 뼈대를 그린다', () => {
    const { container } = render(<Skeleton />);
    const card = container.querySelector('.card');
    expect(card).not.toBeNull();
    expect(card?.querySelectorAll('.sk').length).toBeGreaterThan(0);
  });

  it('보조기기에서는 숨긴다(aria-hidden="true")', () => {
    const { container } = render(<Skeleton />);
    expect(container.querySelector('.card')).toHaveAttribute('aria-hidden', 'true');
  });
});
