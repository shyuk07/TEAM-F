import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { Box } from '@/shared/ui';

describe('shared/ui Box', () => {
  it('tag → title → children 순서로 그린다', () => {
    const { container } = render(
      <Box tag={<span>태그</span>} title="제목">
        <p>본문</p>
      </Box>,
    );
    const box = container.querySelector('.box');
    expect(box?.firstElementChild).toHaveTextContent('태그');
    expect(box?.querySelector('.t')).toHaveTextContent('제목');
    expect(box?.lastElementChild).toHaveTextContent('본문');
  });

  it('tone=done이면 box done이다', () => {
    const { container } = render(<Box title="제목" tone="done" />);
    const box = container.querySelector('.box');
    expect(box).toHaveClass('box', 'done');
  });

  it('title이 없으면 .t를 그리지 않는다', () => {
    const { container } = render(<Box>본문</Box>);
    expect(container.querySelector('.box .t')).toBeNull();
  });
});
