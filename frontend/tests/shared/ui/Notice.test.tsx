import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Notice } from '@/shared/ui';

describe('shared/ui Notice', () => {
  it('warn 클래스로 안내를 그린다', () => {
    render(<Notice>폐점하면 다시 열 수 없어요</Notice>);
    expect(screen.getByText('폐점하면 다시 열 수 없어요')).toHaveClass('warn');
  });
});
