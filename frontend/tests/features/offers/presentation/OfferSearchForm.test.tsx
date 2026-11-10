import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { OfferSearchForm } from '@/features/offers';

describe('OfferSearchForm', () => {
  it('role="search" 폼과 「상품명 검색」 입력이 있다', () => {
    render(<OfferSearchForm keyword={undefined} onSubmit={vi.fn()} />);
    expect(screen.getByRole('search')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('상품명 검색')).toBeInTheDocument();
    expect(screen.getByLabelText('상품명 검색')).toBeInTheDocument();
  });

  it('글자를 입력하는 것만으로는 onSubmit이 불리지 않는다', async () => {
    const onSubmit = vi.fn();
    render(<OfferSearchForm keyword={undefined} onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText('상품명 검색'), '빵');
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('Enter를 누르면 onSubmit(입력값)', async () => {
    const onSubmit = vi.fn();
    render(<OfferSearchForm keyword={undefined} onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText('상품명 검색'), '빵{Enter}');
    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledWith('빵');
  });

  it('빈 입력으로 Enter를 누르면 onSubmit(빈 문자열)', async () => {
    const onSubmit = vi.fn();
    render(<OfferSearchForm keyword={undefined} onSubmit={onSubmit} />);
    await userEvent.type(screen.getByLabelText('상품명 검색'), '{Enter}');
    expect(onSubmit).toHaveBeenCalledWith('');
  });

  it('maxLength가 100이다', () => {
    render(<OfferSearchForm keyword={undefined} onSubmit={vi.fn()} />);
    expect(screen.getByLabelText('상품명 검색')).toHaveAttribute('maxlength', '100');
  });
});
