import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { FieldError } from '@/shared/ui';

describe('shared/ui FieldError', () => {
  it('role=alert와 err 클래스로 오류를 그린다', () => {
    render(<FieldError id="addr-err">주소가 필요해요</FieldError>);
    const el = screen.getByRole('alert');
    expect(el).toHaveClass('err');
    expect(el).toHaveAttribute('id', 'addr-err');
  });
});
