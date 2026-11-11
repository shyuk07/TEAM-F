import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { StoreSuspendedNotice } from '@/features/stores';

describe('features/stores presentation StoreSuspendedNotice', () => {
  it('「상점 정지」 태그(hot), 제목, 설명을 그린다', () => {
    render(<StoreSuspendedNotice />);
    expect(screen.getByText('상점 정지')).toHaveClass('tag', 'hot');
    expect(screen.getByText('관리자가 상점을 정지했어요')).toBeInTheDocument();
    expect(
      screen.getByText('새 할인을 올릴 수 없어요. 기존 예약의 픽업은 처리할 수 있어요.'),
    ).toBeInTheDocument();
  });
});
