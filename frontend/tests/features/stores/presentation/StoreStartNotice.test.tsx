import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { StoreStartNotice } from '@/features/stores';

function renderNotice(view: 'pending' | 'rejected' | 'closed' | 'account-blocked') {
  render(<StoreStartNotice view={view} />);
}

describe('features/stores presentation StoreStartNotice', () => {
  it('pending: 「승인 대기」 태그(tag hot), 제목, 설명을 그린다', () => {
    renderNotice('pending');
    const tag = screen.getByText('승인 대기');
    expect(tag).toHaveClass('tag', 'hot');
    expect(screen.getByText('승인 대기 중이에요')).toBeInTheDocument();
    expect(screen.getByText('관리자가 확인하면 상점을 열 수 있어요.')).toBeInTheDocument();
  });

  it('rejected: 「거절됨」 태그(tag mute), 제목, 설명을 그린다. 「(확인 필요)」 글자는 없다', () => {
    renderNotice('rejected');
    expect(screen.getByText('거절됨')).toHaveClass('tag', 'mute');
    expect(screen.getByText('가입이 거절되었습니다')).toBeInTheDocument();
    expect(screen.getByText('다시 신청하는 기능은 아직 없어요.')).toBeInTheDocument();
    expect(screen.queryByText(/\(확인 필요\)/)).toBeNull();
  });

  it('closed: 「폐점」 태그(tag mute), 제목, 설명을 그린다', () => {
    renderNotice('closed');
    expect(screen.getByText('폐점')).toHaveClass('tag', 'mute');
    expect(screen.getByText('폐점한 상점이에요')).toBeInTheDocument();
    expect(screen.getByText('이 계정으로 새 상점을 열 수 없어요.')).toBeInTheDocument();
  });

  it('account-blocked: 「정지」 태그(tag hot)만 있다', () => {
    renderNotice('account-blocked');
    expect(screen.getByText('정지')).toHaveClass('tag', 'hot');
  });
});
