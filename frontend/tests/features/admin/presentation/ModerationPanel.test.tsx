import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ModerationPanel } from '@/features/admin';
import { renderAdmin } from '../fakes/renderAdmin';

const STORE_ID = '1a2b3c4d-1111-4111-8111-111111111111';

describe('ModerationPanel (M5)', () => {
  it('목록 API 없음 안내를 보인다', () => {
    renderAdmin(<ModerationPanel target="store" />);
    expect(screen.getByText(/상점·할인 목록 API가 아직 없어요/)).toBeInTheDocument();
  });

  it('UUID가 아니면 오류', async () => {
    renderAdmin(<ModerationPanel target="store" />);
    await userEvent.type(screen.getByLabelText('상점 ID 또는 할인 ID'), '1a2b');
    await userEvent.click(screen.getByRole('button', { name: '찾기' }));
    expect(screen.getByRole('alert')).toHaveTextContent('ID 형식이 올바르지 않아요.');
  });

  it('상점 정지 → 응답의 이름·상태(코드 병기)를 보인다', async () => {
    const { repo } = renderAdmin(<ModerationPanel target="store" />);
    await userEvent.type(screen.getByLabelText('상점 ID 또는 할인 ID'), STORE_ID);
    await userEvent.click(screen.getByRole('button', { name: '찾기' }));
    expect(screen.getByText(STORE_ID)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: '정지' }));
    const dialog = screen.getByRole('dialog', { name: '상점 정지' });
    await userEvent.type(within(dialog).getByLabelText('정지 사유 *'), '위생 신고');
    await userEvent.click(within(dialog).getByRole('button', { name: '정지하기' }));
    expect(repo.suspendStore).toHaveBeenCalledWith(STORE_ID, '위생 신고');
    expect(await screen.findByText('망원베이커리')).toBeInTheDocument();
    expect(screen.getByText('SUSPENDED')).toBeInTheDocument();
  });

  it('강제 폐점은 링크에서 M2를 연다', async () => {
    renderAdmin(<ModerationPanel target="store" />);
    await userEvent.type(screen.getByLabelText('상점 ID 또는 할인 ID'), STORE_ID);
    await userEvent.click(screen.getByRole('button', { name: '찾기' }));
    await userEvent.click(screen.getByRole('button', { name: '강제 폐점' }));
    expect(screen.getByRole('dialog', { name: '강제 폐점' })).toBeInTheDocument();
  });

  it('할인 탭은 「할인 정지」', async () => {
    const { repo } = renderAdmin(<ModerationPanel target="offer" />);
    await userEvent.type(screen.getByLabelText('상점 ID 또는 할인 ID'), STORE_ID);
    await userEvent.click(screen.getByRole('button', { name: '찾기' }));
    await userEvent.click(screen.getByRole('button', { name: '할인 정지' }));
    const dialog = screen.getByRole('dialog', { name: '할인 정지' });
    await userEvent.type(within(dialog).getByLabelText('정지 사유 *'), 'x');
    await userEvent.click(within(dialog).getByRole('button', { name: '정지하기' }));
    expect(repo.suspendOffer).toHaveBeenCalledWith(STORE_ID, 'x');
    expect(await screen.findByText('식빵 모둠 5종')).toBeInTheDocument();
  });
});
