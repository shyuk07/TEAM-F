import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { Product } from '@/entities/product';
import { ProductEditForm } from '@/features/products';
import { ApiError } from '@/shared/api/error';
import { baguetteProduct, breadProduct } from '../../../entities/product/fakes/products';
import { deferred } from '../../auth/fakes/deferred';
import { FakeProductCommands } from '../fakes/fakeProductCommands.fake';
import { renderProducts } from '../fakes/renderProducts';

function renderForm(product: Product = breadProduct, commands = new FakeProductCommands()) {
  const onSaved = vi.fn();
  const ctx = renderProducts(<ProductEditForm product={product} onSaved={onSaved} />, {
    commands,
  });
  return { ...ctx, onSaved, commands, user: userEvent.setup() };
}

const nameInput = () => screen.getByLabelText(/^상품명/);
const priceInput = () => screen.getByLabelText(/^정상 가격/);
const categoryInput = () => screen.getByLabelText(/^카테고리/);
const descriptionInput = () => screen.getByLabelText(/^설명/);
const saveBtn = () => screen.getAllByRole('button', { name: '저장' })[0];
const isBlocked = (el: HTMLElement) =>
  el.hasAttribute('disabled') || el.getAttribute('aria-disabled') === 'true';

describe('features/products presentation ProductEditForm', () => {
  it('초기 값이 상품으로 채워지고 사진은 읽기 전용 미리보기다', () => {
    const { container } = renderForm();
    expect(nameInput()).toHaveValue('식빵 모둠 5종');
    expect(priceInput()).toHaveValue('12000');
    expect(categoryInput()).toHaveValue('빵');
    expect(descriptionInput()).toHaveValue('오늘 구운 식빵');
    expect(container.querySelector('img')).toHaveAttribute('src', '/v1/products/p1/images/i1');
    expect(screen.queryByText('사진 바꾸기')).toBeNull();
    expect(screen.queryByText('사진 삭제')).toBeNull();
    expect(screen.getByText('노출 중')).toBeInTheDocument();
    expect(screen.getByText('숨기기')).toBeInTheDocument();
    expect(isBlocked(saveBtn())).toBe(true);
  });

  it('사진이 없는 상품은 사진 칸에 미리보기 img가 없다', () => {
    const { container } = renderForm(baguetteProduct);
    expect(nameInput()).toHaveValue('바게트');
    expect(container.querySelector('img')).toBeNull();
  });

  it('이름을 바꾸면 「저장」이 활성이 되고 update(id, {name})만 보내며 성공하면 onSaved', async () => {
    const commands = new FakeProductCommands();
    const updated = { ...breadProduct, name: '새 이름' };
    commands.update.mockResolvedValue(updated);
    const { user, onSaved } = renderForm(breadProduct, commands);
    await user.clear(nameInput());
    await user.type(nameInput(), '새 이름');
    expect(isBlocked(saveBtn())).toBe(false);
    await user.click(saveBtn());
    await waitFor(() => expect(onSaved).toHaveBeenCalledWith(updated));
    expect(commands.update.mock.calls[0].slice(0, 2)).toEqual(['p1', { name: '새 이름' }]);
  });

  it('가격에 "abc"를 넣고 저장하면 update가 불리지 않고 가격 칸에 오류가 보인다', async () => {
    const { user, commands } = renderForm();
    await user.clear(priceInput());
    await user.type(priceInput(), 'abc');
    await user.click(saveBtn());
    expect(commands.update).not.toHaveBeenCalled();
    expect(await screen.findAllByRole('alert')).not.toHaveLength(0);
  });

  it('카테고리를 비우고 저장하면 update(id, {category: null})', async () => {
    const { user, commands } = renderForm();
    await user.clear(categoryInput());
    await user.click(saveBtn());
    await waitFor(() => expect(commands.update).toHaveBeenCalledTimes(1));
    expect(commands.update.mock.calls[0].slice(0, 2)).toEqual(['p1', { category: null }]);
  });

  it('설명만 비우면 {description: null}만 보낸다', async () => {
    const { user, commands } = renderForm();
    await user.clear(descriptionInput());
    await user.click(saveBtn());
    await waitFor(() => expect(commands.update).toHaveBeenCalledTimes(1));
    expect(commands.update.mock.calls[0][1]).toEqual({ description: null });
  });

  it('이름만 바꾸면 null 키가 없다', async () => {
    const { user, commands } = renderForm();
    await user.type(nameInput(), '!');
    await user.click(saveBtn());
    await waitFor(() => expect(commands.update).toHaveBeenCalledTimes(1));
    const sent = commands.update.mock.calls[0][1];
    expect(Object.keys(sent)).toEqual(['name']);
    expect(Object.values(sent)).not.toContain(null);
  });

  it('저장 중에는 「처리 중…」이고 중복 제출은 update 1회', async () => {
    const commands = new FakeProductCommands();
    const d = deferred<typeof breadProduct>();
    commands.update.mockReturnValue(d.promise);
    const { user } = renderForm(breadProduct, commands);
    await user.type(nameInput(), '!');
    await user.click(saveBtn());
    const busy = await screen.findAllByRole('button', { name: '처리 중…' });
    expect(busy[0]).toHaveAttribute('aria-disabled', 'true');
    await user.click(busy[0]);
    expect(commands.update).toHaveBeenCalledTimes(1);
  });

  // A3: 서버 message는 화면에 나오지 않는다
  it('저장 실패(VALIDATION_ERROR): .err에 공통 문구, 입력값 유지, onSaved 미호출', async () => {
    const commands = new FakeProductCommands();
    commands.update.mockRejectedValue(
      new ApiError(400, 'VALIDATION_ERROR', '정상 가격은 진행 중인 할인 가격보다 커야 합니다.'),
    );
    const { user, onSaved } = renderForm(breadProduct, commands);
    await user.clear(priceInput());
    await user.type(priceInput(), '100');
    await user.click(saveBtn());
    expect(
      await screen.findByText('저장하지 못했어요. 잠시 후 다시 시도해 주세요.'),
    ).toBeInTheDocument();
    expect(screen.queryByText('정상 가격은 진행 중인 할인 가격보다 커야 합니다.')).toBeNull();
    expect(priceInput()).toHaveValue('100');
    expect(onSaved).not.toHaveBeenCalled();
  });

  describe('노출 ↔ 숨김', () => {
    it('「숨기기」: 확인 시트 없이 deactivate(id), 성공하면 칩 「숨김」·「다시 보이기」 버튼, 화면에 남는다', async () => {
      const { user, commands, onSaved } = renderForm();
      await user.click(screen.getByText('숨기기'));
      expect(screen.queryByRole('dialog')).toBeNull();
      expect(screen.queryByRole('alertdialog')).toBeNull();
      await waitFor(() => expect(commands.deactivate).toHaveBeenCalledTimes(1));
      expect(commands.deactivate.mock.calls[0][0]).toBe('p1');
      expect(await screen.findByText('숨김')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '다시 보이기' })).toBeInTheDocument();
      expect(screen.queryByText('숨기기')).toBeNull();
      expect(screen.queryByText('노출 중')).toBeNull();
      expect(onSaved).not.toHaveBeenCalled();
    });

    it('「숨기기」 거절(PRODUCT_HAS_OPEN_OFFER): 칩·링크는 그대로이고 .err에 거절 문구', async () => {
      const commands = new FakeProductCommands();
      commands.deactivate.mockRejectedValue(new ApiError(400, 'PRODUCT_HAS_OPEN_OFFER', 'x'));
      const { user } = renderForm(breadProduct, commands);
      await user.click(screen.getByText('숨기기'));
      expect(
        await screen.findByText(
          '진행 중인 할인이 있어 숨길 수 없어요. 판매를 중단한 뒤 다시 숨겨 주세요.',
        ),
      ).toBeInTheDocument();
      expect(screen.getByText('노출 중')).toBeInTheDocument();
      expect(screen.getByText('숨기기')).toBeInTheDocument();
    });

    // B1(D-33): 이미 원하는 상태면 성공 처리
    it('「숨기기」가 PRODUCT_ALREADY_INACTIVE면 칩 「숨김」·「다시 보이기」로 바뀌고 오류·재조회가 없다', async () => {
      const commands = new FakeProductCommands();
      commands.deactivate.mockRejectedValue(new ApiError(400, 'PRODUCT_ALREADY_INACTIVE', 'x'));
      const { user, repo } = renderForm(breadProduct, commands);
      await user.click(screen.getByText('숨기기'));
      expect(await screen.findByText('숨김')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '다시 보이기' })).toBeInTheDocument();
      expect(screen.queryByRole('alert')).toBeNull();
      expect(repo.findById).not.toHaveBeenCalled();
    });

    it('「다시 보이기」가 PRODUCT_ALREADY_ACTIVE면 칩 「노출 중」·「숨기기」로 바뀌고 오류가 없다', async () => {
      const commands = new FakeProductCommands();
      commands.activate.mockRejectedValue(new ApiError(400, 'PRODUCT_ALREADY_ACTIVE', 'x'));
      const { user } = renderForm(baguetteProduct, commands);
      await user.click(screen.getByRole('button', { name: '다시 보이기' }));
      expect(await screen.findByText('노출 중')).toBeInTheDocument();
      expect(screen.getByText('숨기기')).toBeInTheDocument();
      expect(screen.queryByRole('alert')).toBeNull();
    });

    it('숨김 상품: 칩 「숨김」, 「다시 보이기」 → activate(id), 성공하면 칩 「노출 중」·「숨기기」', async () => {
      const commands = new FakeProductCommands();
      commands.activate.mockResolvedValue({ ...baguetteProduct, isActive: true });
      const { user } = renderForm(baguetteProduct, commands);
      expect(screen.getByText('숨김')).toBeInTheDocument();
      await user.click(screen.getByRole('button', { name: '다시 보이기' }));
      await waitFor(() => expect(commands.activate).toHaveBeenCalledTimes(1));
      expect(commands.activate.mock.calls[0][0]).toBe('p2');
      expect(await screen.findByText('노출 중')).toBeInTheDocument();
      expect(screen.getByText('숨기기')).toBeInTheDocument();
    });

    it('숨기기 중에는 해당 컨트롤이 「처리 중…」이고 비활성이다', async () => {
      const commands = new FakeProductCommands();
      commands.deactivate.mockReturnValue(new Promise(() => {}));
      const { user } = renderForm(breadProduct, commands);
      await user.click(screen.getByText('숨기기'));
      const busy = await screen.findByRole('button', { name: '처리 중…' });
      expect(isBlocked(busy)).toBe(true);
    });

    it('다시 보이기 중에는 해당 컨트롤이 「처리 중…」이고 비활성이다', async () => {
      const commands = new FakeProductCommands();
      commands.activate.mockReturnValue(new Promise(() => {}));
      const { user } = renderForm(baguetteProduct, commands);
      await user.click(screen.getByRole('button', { name: '다시 보이기' }));
      const busy = await screen.findByRole('button', { name: '처리 중…' });
      expect(isBlocked(busy)).toBe(true);
    });
  });
});
