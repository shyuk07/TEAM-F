import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { PhotoField } from '@/features/products/presentation/PhotoField';

type Props = Parameters<typeof PhotoField>[0];

function renderField(over: Partial<Props> = {}) {
  const props: Props = {
    phase: 'empty',
    src: null,
    errorMessage: null,
    hasImage: false,
    onPick: vi.fn(),
    onRemove: vi.fn(),
    onRetry: vi.fn(),
    ...over,
  };
  const result = render(
    <div className="app">
      <PhotoField {...props} />
    </div>,
  );
  return { ...result, props };
}

const isBlocked = (el: HTMLElement) =>
  el.hasAttribute('disabled') || el.getAttribute('aria-disabled') === 'true';

describe('features/products presentation PhotoField', () => {
  it('empty: 「사진 추가」 문구가 보이고 누르면 선택 시트가 열린다', async () => {
    const { container } = renderField({ phase: 'empty' });
    expect(container.querySelector('img')).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: /사진 추가/ }));
    expect(await screen.findByText('카메라로 찍기')).toBeInTheDocument();
    expect(screen.getByText('앨범에서 고르기')).toBeInTheDocument();
  });

  it('filled: 미리보기 이미지와 「사진 바꾸기」·삭제 링크가 보인다', async () => {
    const { container, props } = renderField({
      phase: 'filled',
      src: 'blob:preview-1',
      hasImage: true,
    });
    expect(container.querySelector('img')).toHaveAttribute('src', 'blob:preview-1');
    expect(screen.getByRole('button', { name: '사진 바꾸기' })).toBeInTheDocument();
    await userEvent.click(screen.getByText('삭제'));
    expect(props.onRemove).toHaveBeenCalledTimes(1);
  });

  // B2: 등록 중 「취소」는 없다
  it('uploading: 「올리는 중…」만 있고 취소가 없으며 진행 막대·퍼센트도 없다', () => {
    const { container } = renderField({
      phase: 'uploading',
      src: 'blob:preview-1',
      hasImage: true,
    });
    expect(screen.getByText('올리는 중…')).toBeInTheDocument();
    expect(screen.queryByText('취소')).toBeNull();
    expect(screen.queryByRole('progressbar')).toBeNull();
    expect(container.textContent ?? '').not.toMatch(/\d+\s*%/);
  });

  // D-34
  it('failed인데 onRetry를 넘기지 않으면 「다시 시도」가 없고 「다른 사진 고르기」만 있다', () => {
    renderField({
      phase: 'failed',
      errorMessage: '사진이 5MB보다 커요. 더 작은 사진을 골라 주세요.',
      onRetry: undefined,
    });
    expect(screen.getByRole('button', { name: '다른 사진 고르기' })).toBeInTheDocument();
    expect(screen.queryByText('다시 시도')).toBeNull();
  });

  it('failed: 오류 문구, 「다시 시도」, 「다른 사진 고르기」가 보인다', async () => {
    const { props } = renderField({
      phase: 'failed',
      errorMessage: '사진이 5MB보다 커요. 더 작은 사진을 골라 주세요.',
      src: 'blob:preview-1',
      hasImage: true,
    });
    expect(
      screen.getByText('사진이 5MB보다 커요. 더 작은 사진을 골라 주세요.'),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByText('다시 시도'));
    expect(props.onRetry).toHaveBeenCalledTimes(1);
    await userEvent.click(screen.getByRole('button', { name: '다른 사진 고르기' }));
    expect(await screen.findByText('카메라로 찍기')).toBeInTheDocument();
  });

  it('src가 빈 문자열이면 이미지를 그리지 않는다', () => {
    const { container } = renderField({ phase: 'filled', src: '', hasImage: true });
    expect(screen.getByRole('button', { name: '사진 바꾸기' })).toBeInTheDocument();
    expect(container.querySelector('img')).toBeNull();
  });

  it('disabled이면 버튼이 비활성이다', () => {
    renderField({ phase: 'filled', src: 'blob:preview-1', hasImage: true, disabled: true });
    expect(isBlocked(screen.getByRole('button', { name: '사진 바꾸기' }))).toBe(true);
  });
});
