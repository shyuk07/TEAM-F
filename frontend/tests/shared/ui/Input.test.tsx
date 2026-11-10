import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { Input } from '@/shared/ui';

function renderInput(overrides = {}) {
  const props = { label: '픽업 주소', value: '', onChange: vi.fn(), ...overrides };
  render(<Input {...props} />);
  // 실제 props에 붙은 onChange를 돌려준다(D-결정 2026-11-10: 헬퍼 내부 mock이 아니라 바인딩된 mock)
  return { onChange: props.onChange };
}

describe('shared/ui Input', () => {
  it('label과 입력이 getByLabelText로 연결된다', () => {
    renderInput();
    expect(screen.getByLabelText('픽업 주소')).toBeInTheDocument();
  });

  it('required면 라벨 끝에 *가 붙는다', () => {
    renderInput({ label: '픽업 주소', required: true, value: '', onChange: vi.fn() });
    expect(screen.getByLabelText(/픽업 주소 \*/)).toBeInTheDocument();
  });

  it('error가 있으면 alert 역할 오류를 표시하고 aria-invalid·aria-describedby를 채운다', () => {
    renderInput({ error: '주소를 입력해 주세요.', value: '', onChange: vi.fn() });
    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('주소를 입력해 주세요.');
    expect(screen.getByLabelText('픽업 주소')).toHaveAttribute('aria-invalid', 'true');
    expect(screen.getByLabelText('픽업 주소')).toHaveAttribute(
      'aria-describedby',
      expect.stringMatching(/.+/),
    );
  });

  it('error가 없으면 alert이 없다', () => {
    renderInput({ value: '', onChange: vi.fn() });
    expect(screen.queryByRole('alert')).toBeNull();
  });

  it('readOnly면 in ro 클래스와 readonly 속성이 있다', () => {
    renderInput({
      value: '망원베이커리',
      readOnly: true,
      label: '상점명 (가입 시 상호)',
      onChange: vi.fn(),
    });
    const input = screen.getByLabelText('상점명 (가입 시 상호)');
    expect(input).toHaveClass('in', 'ro');
    expect(input).toHaveAttribute('readonly');
  });

  it('onChange는 문자열 값을 받는다', async () => {
    const { onChange } = renderInput({ value: '', onChange: vi.fn() });
    await userEvent.type(screen.getByLabelText('픽업 주소'), '서');
    expect(onChange).toHaveBeenCalledWith('서');
  });

  it('maxLength를 전달한다', () => {
    renderInput({ maxLength: 500, value: '', onChange: vi.fn() });
    expect(screen.getByLabelText('픽업 주소')).toHaveAttribute('maxlength', '500');
  });
});
