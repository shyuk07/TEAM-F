import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { CtaBar } from '@/shared/ui';

describe('shared/ui CtaBar', () => {
  it('cta 클래스로 자식을 감싼다', () => {
    render(
      <CtaBar>
        <button type="button">다음</button>
      </CtaBar>,
    );
    const bar = screen.getByRole('button', { name: '다음' }).parentElement;
    expect(bar).toHaveClass('cta');
  });
});
