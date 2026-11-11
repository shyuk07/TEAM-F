import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { PhotoPickSheet } from '@/features/products/presentation/PhotoPickSheet';
import { makeFile } from '../../../support/objectUrl';

function renderSheet() {
  const onPick = vi.fn();
  const onClose = vi.fn();
  render(
    <div className="app">
      <PhotoPickSheet onPick={onPick} onClose={onClose} />
    </div>,
  );
  return { onPick, onClose };
}

const albumInput = () =>
  document.querySelector<HTMLInputElement>('input[type="file"]:not([capture])');
const cameraInput = () => document.querySelector<HTMLInputElement>('input[capture="environment"]');

describe('features/products presentation PhotoPickSheet', () => {
  it('제목·두 버튼·안내 문구가 보인다', () => {
    renderSheet();
    expect(screen.getByText('사진 추가')).toBeInTheDocument();
    expect(screen.getByText('카메라로 찍기')).toBeInTheDocument();
    expect(screen.getByText('앨범에서 고르기')).toBeInTheDocument();
    expect(screen.getByText('JPG·PNG·WebP, 5MB 이하')).toBeInTheDocument();
  });

  it('카메라 입력은 capture="environment", 앨범 입력은 세 형식을 받는다', () => {
    renderSheet();
    expect(cameraInput()).not.toBeNull();
    expect(cameraInput()).toHaveAttribute('type', 'file');
    const accept = albumInput()?.getAttribute('accept') ?? '';
    expect(accept).toContain('image/jpeg');
    expect(accept).toContain('image/png');
    expect(accept).toContain('image/webp');
  });

  it('앨범에서 파일을 고르면 onPick(file) 뒤 onClose가 불린다', () => {
    const { onPick, onClose } = renderSheet();
    const file = makeFile('image/jpeg', 100, 'a.jpg');
    const input = albumInput();
    expect(input).not.toBeNull();
    fireEvent.change(input as HTMLInputElement, { target: { files: [file] } });
    expect(onPick).toHaveBeenCalledWith(file);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('「취소」를 누르면 onClose', async () => {
    const { onClose, onPick } = renderSheet();
    await userEvent.click(screen.getByText('취소'));
    expect(onClose).toHaveBeenCalledTimes(1);
    expect(onPick).not.toHaveBeenCalled();
  });

  it('Esc를 누르면 onClose', async () => {
    const { onClose } = renderSheet();
    await userEvent.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('딤 영역을 누르면 onClose', async () => {
    const { onClose } = renderSheet();
    const dim = document.querySelector('.dim');
    expect(dim).not.toBeNull();
    await userEvent.click(dim as HTMLElement);
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
