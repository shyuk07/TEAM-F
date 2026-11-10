import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { FormEvent } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { Button } from '@/shared/ui';

describe('shared/ui Button', () => {
  it('기본 className은 btn이고 type은 button이다', () => {
    render(<Button>저장</Button>);
    const btn = screen.getByRole('button', { name: '저장' });
    expect(btn).toHaveClass('btn');
    expect(btn).toHaveAttribute('type', 'button');
  });

  it.each([
    ['primary' as const, 'pri'],
    ['dark' as const, 'dark'],
  ])('variant가 %s면 %s 클래스를 붙인다', (variant, cls) => {
    render(<Button variant={variant}>저장</Button>);
    expect(screen.getByRole('button')).toHaveClass(cls);
  });

  it('size가 sm이면 sm 클래스를 붙인다', () => {
    render(
      <Button size="sm" variant="primary">
        행
      </Button>,
    );
    expect(screen.getByRole('button')).toHaveClass('sm', 'pri');
  });

  it('desktopOnly면 dk 클래스를 붙인다', () => {
    render(<Button desktopOnly>상점 열기</Button>);
    expect(screen.getByRole('button')).toHaveClass('dk');
  });

  it('disabled면 aria-disabled=true이고 onClick이 불리지 않는다', async () => {
    const onClick = vi.fn();
    render(
      <Button disabled onClick={onClick}>
        폐점하기
      </Button>,
    );
    const btn = screen.getByRole('button', { name: '폐점하기' });
    expect(btn).toHaveAttribute('aria-disabled', 'true');
    await userEvent.click(btn);
    expect(onClick).not.toHaveBeenCalled();
  });

  it('pending이면 이름이 「처리 중…」이고 클릭이 무시된다', async () => {
    const onClick = vi.fn();
    render(
      <Button pending onClick={onClick}>
        상점 열기
      </Button>,
    );
    const btn = screen.getByRole('button', { name: '처리 중…' });
    await userEvent.click(btn);
    expect(onClick).not.toHaveBeenCalled();
  });

  it('type=submit인데 disabled면 폼 제출이 막힌다', async () => {
    const submitted = vi.fn();
    const onSubmit = (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault();
      submitted();
    };
    render(
      <form onSubmit={onSubmit} action="#">
        <Button type="submit" disabled>
          등록
        </Button>
      </form>,
    );
    await userEvent.click(screen.getByText('등록'));
    expect(submitted).not.toHaveBeenCalled();
  });

  it('form 속성을 그대로 전달한다', () => {
    render(
      <Button type="submit" form="open-store">
        상점 열기
      </Button>,
    );
    expect(screen.getByRole('button')).toHaveAttribute('form', 'open-store');
  });
});
