import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { AppBar } from '@/shared/ui';

describe('shared/ui AppBar', () => {
  it('logo가 없으면 .t로 제목을 그린다', () => {
    render(<AppBar title="상점 폐점" />);
    const bar = screen.getByText('상점 폐점');
    expect(bar).toHaveClass('t');
    expect(bar).not.toHaveClass('logo');
  });

  it('logo면 logo 클래스로 제목을 그린다', () => {
    render(<AppBar title="마감직전 상점주" logo />);
    expect(screen.getByText('마감직전 상점주')).toHaveClass('logo');
  });

  it('left와 right를 제목 앞뒤로 배치한다', () => {
    render(
      <AppBar
        title="상점 폐점"
        left={<button type="button">←</button>}
        right={<button type="button">로그아웃</button>}
      />,
    );
    const bar = screen.getByText('상점 폐점').parentElement;
    expect(bar?.firstElementChild).toHaveTextContent('←');
    expect(bar?.lastElementChild).toHaveTextContent('로그아웃');
  });
});
