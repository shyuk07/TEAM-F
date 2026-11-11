import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { EmptyState } from '@/shared/ui';

describe('shared/ui EmptyState', () => {
  it('제목·설명·action을 그린다', () => {
    const { container } = render(
      <EmptyState title="비었어요" description="채워 보세요" action={<button>추가</button>} />,
    );
    expect(container.querySelector('.box.empty')).not.toBeNull();
    expect(screen.getByText('비었어요')).toBeInTheDocument();
    expect(screen.getByText('채워 보세요')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '추가' })).toBeInTheDocument();
  });

  it('description·action이 없으면 그 요소가 없다', () => {
    const { container } = render(<EmptyState title="비었어요" />);
    expect(screen.getByText('비었어요')).toBeInTheDocument();
    expect(container.querySelector('.m')).toBeNull();
    expect(screen.queryByRole('button')).toBeNull();
  });
});
