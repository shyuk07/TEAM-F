import { act, renderHook } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { usePhotoDraft } from '@/features/products/application/usePhotoDraft';
import { makeFile, useFakeObjectUrl } from '../../../support/objectUrl';

const TOO_LARGE = '사진이 5MB보다 커요. 더 작은 사진을 골라 주세요.';
const BAD_TYPE = 'JPG, PNG, WebP 사진만 올릴 수 있어요.';

describe('features/products application usePhotoDraft', () => {
  const url = useFakeObjectUrl();

  it('처음에는 file·previewSrc·error가 모두 null', () => {
    const { result } = renderHook(() => usePhotoDraft());
    expect(result.current.file).toBeNull();
    expect(result.current.previewSrc).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('정상 파일을 pick하면 file·previewSrc가 설정되고 error는 null', () => {
    const { result } = renderHook(() => usePhotoDraft());
    const file = makeFile('image/jpeg', 1000);
    act(() => result.current.pick(file));
    expect(result.current.file).toBe(file);
    expect(result.current.previewSrc).toBe('blob:preview-1');
    expect(result.current.error).toBeNull();
  });

  // A2: 검증 실패 시 이전 사진을 버린다
  it('6MB 파일은 이전 사진을 버리고 error만 설정한다', () => {
    const { result } = renderHook(() => usePhotoDraft());
    act(() => result.current.pick(makeFile('image/jpeg', 1000)));
    act(() => result.current.pick(makeFile('image/jpeg', 6 * 1024 * 1024)));
    expect(result.current.error).toBe(TOO_LARGE);
    expect(result.current.file).toBeNull();
    expect(result.current.previewSrc).toBeNull();
    expect(url.revoke).toHaveBeenCalledWith('blob:preview-1');
  });

  it('image/gif는 형식 문구, 처음부터 비어 있던 상태는 그대로 비어 있다', () => {
    const { result } = renderHook(() => usePhotoDraft());
    act(() => result.current.pick(makeFile('image/gif', 1000)));
    expect(result.current.error).toBe(BAD_TYPE);
    expect(result.current.file).toBeNull();
    expect(result.current.previewSrc).toBeNull();
  });

  it('정상 파일 뒤 image/gif를 고르면 형식 문구, 사진은 비고 이전 미리보기는 revoke 1회(A2)', () => {
    const { result } = renderHook(() => usePhotoDraft());
    act(() => result.current.pick(makeFile('image/jpeg', 1000)));
    act(() => result.current.pick(makeFile('image/gif', 1000)));
    expect(result.current.error).toBe(BAD_TYPE);
    expect(result.current.file).toBeNull();
    expect(result.current.previewSrc).toBeNull();
    expect(url.revoke).toHaveBeenCalledTimes(1);
    expect(url.revoke).toHaveBeenCalledWith('blob:preview-1');
  });

  it('검증 실패 뒤 정상 파일을 고르면 error가 지워지고 새 미리보기가 생긴다(A2)', () => {
    const { result } = renderHook(() => usePhotoDraft());
    act(() => result.current.pick(makeFile('image/gif', 1000)));
    const good = makeFile('image/png', 2000);
    act(() => result.current.pick(good));
    expect(result.current.error).toBeNull();
    expect(result.current.file).toBe(good);
    expect(result.current.previewSrc).toBe('blob:preview-1');
  });

  it('두 번째 pick이 성공하면 이전 미리보기 URL을 revoke한다', () => {
    const { result } = renderHook(() => usePhotoDraft());
    act(() => result.current.pick(makeFile('image/jpeg', 1000)));
    act(() => result.current.pick(makeFile('image/png', 2000)));
    expect(url.revoke).toHaveBeenCalledWith('blob:preview-1');
    expect(result.current.previewSrc).toBe('blob:preview-2');
  });

  it('clear()는 file·previewSrc를 null로 만들고 미리보기를 revoke한다', () => {
    const { result } = renderHook(() => usePhotoDraft());
    act(() => result.current.pick(makeFile('image/jpeg', 1000)));
    act(() => result.current.clear());
    expect(result.current.file).toBeNull();
    expect(result.current.previewSrc).toBeNull();
    expect(url.revoke).toHaveBeenCalledWith('blob:preview-1');
  });

  it('언마운트하면 마지막 미리보기를 revoke한다', () => {
    const { result, unmount } = renderHook(() => usePhotoDraft());
    act(() => result.current.pick(makeFile('image/jpeg', 1000)));
    expect(url.revoke).not.toHaveBeenCalled();
    unmount();
    expect(url.revoke).toHaveBeenCalledWith('blob:preview-1');
  });
});
