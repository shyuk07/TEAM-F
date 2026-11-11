import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { ProductCreateForm } from '@/features/products';
import { ApiError } from '@/shared/api/error';
import { createdProduct } from '../../../entities/product/fakes/products';
import { deferred } from '../../auth/fakes/deferred';
import { makeFile, useFakeObjectUrl } from '../../../support/objectUrl';
import { FakeProductCommands } from '../fakes/fakeProductCommands.fake';
import { renderProducts } from '../fakes/renderProducts';

const TOO_LARGE = '사진이 5MB보다 커요. 더 작은 사진을 골라 주세요.';

function renderForm(commands = new FakeProductCommands()) {
  const onCreated = vi.fn();
  const ctx = renderProducts(<ProductCreateForm storeId="s1" onCreated={onCreated} />, {
    commands,
  });
  return { ...ctx, onCreated, commands, user: userEvent.setup() };
}

const nameInput = () => screen.getByLabelText(/^상품명/);
const priceInput = () => screen.getByLabelText(/^정상 가격/);
const categoryInput = () => screen.getByLabelText(/^카테고리/);
const descriptionInput = () => screen.getByLabelText(/^설명/);
// 같은 동작 버튼이 본문과 CtaBar에 두 벌 있을 수 있어 첫 번째를 쓴다.
const btn = (name: string | RegExp) => screen.getAllByRole('button', { name })[0];

async function fillRequired(user: ReturnType<typeof userEvent.setup>) {
  await user.type(nameInput(), '식빵');
  await user.type(priceInput(), '12000');
}

async function pickPhoto(file: File) {
  await userEvent.click(screen.getByRole('button', { name: /사진 추가/ }));
  const input = document.querySelector<HTMLInputElement>('input[type="file"]:not([capture])');
  expect(input).not.toBeNull();
  fireEvent.change(input as HTMLInputElement, { target: { files: [file] } });
}

describe('features/products presentation ProductCreateForm', () => {
  useFakeObjectUrl();

  it('초기: 라벨 5개, 사진 칸 empty, 두 제출 버튼', () => {
    renderForm();
    expect(nameInput()).toBeInTheDocument();
    expect(priceInput()).toBeInTheDocument();
    expect(categoryInput()).toBeInTheDocument();
    expect(descriptionInput()).toBeInTheDocument();
    expect(screen.getByText(/상품 사진 \(1장\)/)).toBeInTheDocument();
    expect(screen.getByText(/사진 추가 · 카메라 또는 앨범/)).toBeInTheDocument();
    expect(btn('등록하고 할인 만들기')).toBeInTheDocument();
    expect(btn('등록만')).toBeInTheDocument();
  });

  // D-37: 데스크톱(.cta 숨김)에서도 할인 없이 등록할 수 있게 .dk에 「등록만」을 둔다
  it('데스크톱 .dk: 「등록만」(보조)이 「등록하고 할인 만들기」(primary) 앞에 있고 둘 다 .cta 밖이다', () => {
    const { container } = renderForm();
    const dk = Array.from(container.querySelectorAll<HTMLElement>('.dk'));
    expect(dk.map((b) => b.textContent)).toEqual(['등록만', '등록하고 할인 만들기']);
    expect(dk[0]).not.toHaveClass('pri');
    expect(dk[1]).toHaveClass('pri');
    for (const b of dk) expect(b.closest('.cta')).toBeNull();
    const cta = container.querySelector('.cta') as HTMLElement;
    expect(within(cta).getByRole('button', { name: '등록만' })).toBeInTheDocument();
    expect(within(cta).getByRole('button', { name: '등록하고 할인 만들기' })).toBeInTheDocument();
  });

  it('데스크톱 「등록만」(.dk)을 누르면 사진 없이 create를 부르고 onCreated(product, "list")', async () => {
    const { commands, onCreated, user, container } = renderForm();
    await fillRequired(user);
    const dkList = container.querySelector('.dk') as HTMLElement;
    expect(dkList).toHaveTextContent('등록만');
    await user.click(dkList);
    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(createdProduct, 'list'));
    expect(commands.create.mock.calls[0].slice(0, 3)).toEqual([
      's1',
      { name: '식빵', originalPrice: 12000, category: null, description: null },
      null,
    ]);
  });

  it('제출 중에는 모바일·데스크톱 4개 버튼이 모두 「처리 중…」·aria-disabled다', async () => {
    const commands = new FakeProductCommands();
    commands.create.mockReturnValue(new Promise(() => {}));
    const { user, container } = renderForm(commands);
    await fillRequired(user);
    await user.click(container.querySelector('.dk') as HTMLElement);
    await waitFor(() =>
      expect(container.querySelectorAll('.cta .btn, .dk[aria-disabled="true"]')).toHaveLength(4),
    );
    for (const b of Array.from(container.querySelectorAll<HTMLElement>('.cta .btn, .dk'))) {
      expect(b).toHaveTextContent('처리 중…');
      expect(b).toHaveAttribute('aria-disabled', 'true');
    }
  });

  // D-38: 360px에서 「등록하고 할인 만들기」가 줄바꿈되지 않게 모바일 「등록만」은 내용 폭만 쓴다
  it('모바일 .cta 안 「등록만」만 style.flex가 "0 0 auto"이고 나머지 버튼에는 style이 없다', () => {
    const { container } = renderForm();
    const cta = container.querySelector('.cta') as HTMLElement;
    const listBtn = within(cta).getByRole('button', { name: '등록만' });
    expect(listBtn.style.flex).toBe('0 0 auto');
    expect(within(cta).getByRole('button', { name: '등록하고 할인 만들기' })).not.toHaveAttribute(
      'style',
    );
    for (const b of Array.from(container.querySelectorAll('.dk'))) {
      expect(b).not.toHaveAttribute('style');
    }
  });

  it('빈 상태로 제출하면 create가 불리지 않고 이름·가격 칸에 오류가 보인다', async () => {
    const { commands, user } = renderForm();
    await user.click(btn('등록만'));
    expect(commands.create).not.toHaveBeenCalled();
    expect(await screen.findAllByRole('alert')).toHaveLength(2);
  });

  it('이름+가격 입력 후 「등록만」 → create 호출, 성공하면 onCreated(product, "list")', async () => {
    const { commands, onCreated, user } = renderForm();
    await fillRequired(user);
    await user.click(btn('등록만'));
    await waitFor(() => expect(onCreated).toHaveBeenCalledTimes(1));
    expect(commands.create).toHaveBeenCalledTimes(1);
    expect(commands.create.mock.calls[0].slice(0, 3)).toEqual([
      's1',
      { name: '식빵', originalPrice: 12000, category: null, description: null },
      null,
    ]);
    expect(onCreated).toHaveBeenCalledWith(createdProduct, 'list');
  });

  it('카테고리·설명을 입력하면 그 값이 create에 담긴다(빈 칸이 아니면 null이 아님)', async () => {
    const { commands, user } = renderForm();
    await fillRequired(user);
    await user.type(categoryInput(), '빵');
    await user.type(descriptionInput(), '오늘 구운 식빵');
    await user.click(btn('등록만'));
    await waitFor(() => expect(commands.create).toHaveBeenCalledTimes(1));
    expect(commands.create.mock.calls[0][1]).toEqual({
      name: '식빵',
      originalPrice: 12000,
      category: '빵',
      description: '오늘 구운 식빵',
    });
  });

  it('「등록하고 할인 만들기」 → onCreated(product, "offer")', async () => {
    const { onCreated, user } = renderForm();
    await fillRequired(user);
    await user.click(btn('등록하고 할인 만들기'));
    await waitFor(() => expect(onCreated).toHaveBeenCalledWith(createdProduct, 'offer'));
  });

  it('정상 사진을 고르면 미리보기·「사진 바꾸기」·「삭제」가 보이고 제출 시 create 3번째 인자가 그 파일', async () => {
    const { commands, user, container } = renderForm();
    const file = makeFile('image/jpeg', 1000, 'a.jpg');
    await pickPhoto(file);
    expect(container.querySelector('img')).toHaveAttribute('src', 'blob:preview-1');
    expect(screen.getByRole('button', { name: '사진 바꾸기' })).toBeInTheDocument();
    expect(screen.getByText('삭제')).toBeInTheDocument();
    await fillRequired(user);
    await user.click(btn('등록만'));
    await waitFor(() => expect(commands.create).toHaveBeenCalledTimes(1));
    expect(commands.create.mock.calls[0][2]).toBe(file);
  });

  // A2: 검증 실패한 사진은 보관하지 않으므로 「다시 시도」가 없고 제출 시 사진은 null
  it('6MB 파일을 고르면 사진 칸이 failed(5MB 문구, 미리보기 없음, 다른 사진 고르기만)이고 제출 시 사진은 null', async () => {
    const { commands, user, container } = renderForm();
    const big = makeFile('image/jpeg', 6 * 1024 * 1024, 'big.jpg');
    await pickPhoto(big);
    expect(await screen.findByText(TOO_LARGE)).toBeInTheDocument();
    expect(container.querySelector('img')).toBeNull();
    expect(screen.getByRole('button', { name: '다른 사진 고르기' })).toBeInTheDocument();
    expect(screen.queryByText('다시 시도')).toBeNull();
    await fillRequired(user);
    await user.click(btn('등록만'));
    await waitFor(() => expect(commands.create).toHaveBeenCalledTimes(1));
    expect(commands.create.mock.calls[0][2]).toBeNull();
  });

  it('정상 사진을 고른 뒤 6MB 사진을 고르면 이전 미리보기가 사라지고 제출 시 사진은 null(A2)', async () => {
    const { commands, user, container } = renderForm();
    await pickPhoto(makeFile('image/jpeg', 1000, 'ok.jpg'));
    expect(container.querySelector('img')).not.toBeNull();
    await user.click(screen.getByRole('button', { name: '사진 바꾸기' }));
    const input = document.querySelector<HTMLInputElement>('input[type="file"]:not([capture])');
    fireEvent.change(input as HTMLInputElement, {
      target: { files: [makeFile('image/jpeg', 6 * 1024 * 1024, 'big.jpg')] },
    });
    expect(await screen.findByText(TOO_LARGE)).toBeInTheDocument();
    expect(container.querySelector('img')).toBeNull();
    await fillRequired(user);
    await user.click(btn('등록만'));
    await waitFor(() => expect(commands.create).toHaveBeenCalledTimes(1));
    expect(commands.create.mock.calls[0][2]).toBeNull();
  });

  it('검증 실패 뒤 「다른 사진 고르기」로 정상 파일을 고르면 filled로 돌아오고 오류 문구가 사라진다(A2)', async () => {
    const { user, container } = renderForm();
    await pickPhoto(makeFile('image/jpeg', 6 * 1024 * 1024, 'big.jpg'));
    await user.click(await screen.findByRole('button', { name: '다른 사진 고르기' }));
    const input = document.querySelector<HTMLInputElement>('input[type="file"]:not([capture])');
    fireEvent.change(input as HTMLInputElement, {
      target: { files: [makeFile('image/png', 1000, 'ok.png')] },
    });
    expect(await screen.findByRole('button', { name: '사진 바꾸기' })).toBeInTheDocument();
    expect(container.querySelector('img')).toHaveAttribute('src', 'blob:preview-1');
    expect(screen.queryByText(TOO_LARGE)).toBeNull();
  });

  it('「삭제」를 누르면 사진 칸이 empty로 돌아가고 제출 시 사진은 null', async () => {
    const { commands, user } = renderForm();
    await pickPhoto(makeFile('image/png', 1000));
    await user.click(screen.getByText('삭제'));
    expect(screen.getByText(/사진 추가 · 카메라 또는 앨범/)).toBeInTheDocument();
    await fillRequired(user);
    await user.click(btn('등록만'));
    await waitFor(() => expect(commands.create).toHaveBeenCalledTimes(1));
    expect(commands.create.mock.calls[0][2]).toBeNull();
  });

  describe('제출 중', () => {
    function pending() {
      const commands = new FakeProductCommands();
      const d = deferred<typeof createdProduct>();
      commands.create.mockReturnValue(d.promise);
      return { commands, d };
    }

    // B2: 사진이 있을 때만 「올리는 중…」, 등록 중 「취소」는 없다
    it('두 버튼이 「처리 중…」·aria-disabled, 사진 칸은 「올리는 중…」, 취소 없음, 입력 칸은 비활성', async () => {
      const { commands } = pending();
      const { user } = renderForm(commands);
      await pickPhoto(makeFile('image/jpeg', 1000));
      await fillRequired(user);
      await user.click(btn('등록만'));
      const busy = await screen.findAllByRole('button', { name: '처리 중…' });
      expect(busy.length).toBeGreaterThanOrEqual(2);
      for (const b of busy) expect(b).toHaveAttribute('aria-disabled', 'true');
      expect(screen.getByText('올리는 중…')).toBeInTheDocument();
      expect(screen.queryByText('취소')).toBeNull();
      expect(nameInput()).toBeDisabled();
      expect(priceInput()).toBeDisabled();
    });

    it('사진 없이 제출하면 「올리는 중…」이 없고 사진 칸은 empty 그대로, 취소 없음(B2)', async () => {
      const { commands } = pending();
      const { user } = renderForm(commands);
      await fillRequired(user);
      await user.click(btn('등록만'));
      const busy = await screen.findAllByRole('button', { name: '처리 중…' });
      expect(busy.length).toBeGreaterThanOrEqual(2);
      expect(screen.queryByText('올리는 중…')).toBeNull();
      expect(screen.getByText(/사진 추가 · 카메라 또는 앨범/)).toBeInTheDocument();
      expect(screen.queryByText('취소')).toBeNull();
    });

    it('제출 중 폼을 언마운트하면 create에 넘긴 signal이 abort된다(B2, F10)', async () => {
      const { commands } = pending();
      const { user, unmount } = renderForm(commands);
      await fillRequired(user);
      await user.click(btn('등록만'));
      await screen.findAllByRole('button', { name: '처리 중…' });
      const signal = commands.create.mock.calls[0][3];
      expect(signal?.aborted).toBe(false);
      unmount();
      expect(signal?.aborted).toBe(true);
    });

    it('제출 중 버튼을 한 번 더 눌러도 create는 1회', async () => {
      const { commands } = pending();
      const { user } = renderForm(commands);
      await fillRequired(user);
      await user.click(btn('등록만'));
      const busy = await screen.findAllByRole('button', { name: '처리 중…' });
      await user.click(busy[0]);
      expect(commands.create).toHaveBeenCalledTimes(1);
    });
  });

  it('IMAGE_TOO_LARGE: 사진 칸 failed + 5MB 문구, 입력값 유지, 「다시 시도」는 같은 입력으로 재호출, 「다른 사진 고르기」는 시트를 연다', async () => {
    const commands = new FakeProductCommands();
    commands.create.mockRejectedValue(new ApiError(400, 'IMAGE_TOO_LARGE', 'x'));
    const { user } = renderForm(commands);
    const file = makeFile('image/jpeg', 1000);
    await pickPhoto(file);
    await fillRequired(user);
    await user.click(btn('등록만'));
    expect(await screen.findByText(TOO_LARGE)).toBeInTheDocument();
    expect(nameInput()).toHaveValue('식빵');
    expect(priceInput()).toHaveValue('12000');
    await user.click(screen.getByText('다시 시도'));
    await waitFor(() => expect(commands.create).toHaveBeenCalledTimes(2));
    expect(commands.create.mock.calls[1].slice(0, 3)).toEqual(
      commands.create.mock.calls[0].slice(0, 3),
    );
    await user.click(await screen.findByRole('button', { name: '다른 사진 고르기' }));
    expect(await screen.findByText('카메라로 찍기')).toBeInTheDocument();
  });

  it('STORE_SUSPENDED: 폼 위 .err에 정지 문구, 입력값 유지, 사진 칸은 failed가 아니다', async () => {
    const commands = new FakeProductCommands();
    commands.create.mockRejectedValue(new ApiError(400, 'STORE_SUSPENDED', 'x'));
    const { user } = renderForm(commands);
    await fillRequired(user);
    await user.click(btn('등록만'));
    expect(
      await screen.findByText('정지된 상점에서는 상품을 등록할 수 없어요.'),
    ).toBeInTheDocument();
    expect(nameInput()).toHaveValue('식빵');
    expect(priceInput()).toHaveValue('12000');
    expect(screen.queryByText('다른 사진 고르기')).toBeNull();
  });

  it('「사진 추가」를 누르면 선택 시트가 열리고 「취소」로 닫히며 포커스가 열었던 버튼으로 돌아간다', async () => {
    const { user } = renderForm();
    const opener = screen.getByRole('button', { name: /사진 추가/ });
    await user.click(opener);
    expect(await screen.findByText('카메라로 찍기')).toBeInTheDocument();
    expect(screen.getByText('앨범에서 고르기')).toBeInTheDocument();
    await user.click(screen.getByText('취소'));
    expect(screen.queryByText('카메라로 찍기')).toBeNull();
    expect(opener).toHaveFocus();
  });
});
