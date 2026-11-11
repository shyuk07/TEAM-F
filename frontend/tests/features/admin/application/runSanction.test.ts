import { runSanction } from '@/features/admin/application/runSanction';
import { FakeAdminRepository } from '../fakes/fakeAdminRepository.fake';

describe('runSanction', () => {
  const until = new Date(2026, 10, 30, 23, 59, 59, 999);

  it('회원 정지는 사유와 종료 시각을 넘긴다', async () => {
    const admin = new FakeAdminRepository();
    await expect(
      runSanction({ admin }, 'suspendUser', 'u1', { reason: '노쇼', until }),
    ).resolves.toEqual({ kind: 'user' });
    expect(admin.suspendUser).toHaveBeenCalledWith('u1', '노쇼', until);
  });

  it('상점주 거부', async () => {
    const admin = new FakeAdminRepository();
    await runSanction({ admin }, 'rejectOwner', 'u1', { reason: 'x', until: null });
    expect(admin.rejectOwner).toHaveBeenCalledWith('u1', 'x');
  });

  it('강제 탈퇴는 취소 예약 수를 돌려준다', async () => {
    const admin = new FakeAdminRepository();
    admin.withdrawUser.mockResolvedValue({ cancelledReservationCount: 3 });
    await expect(
      runSanction({ admin }, 'withdrawUser', 'u1', { reason: 'x', until: null }),
    ).resolves.toEqual({ kind: 'withdrawn', cancelledReservationCount: 3 });
  });

  it('상점 정지·강제 폐점·할인 정지는 결과 대상을 돌려준다', async () => {
    const admin = new FakeAdminRepository();
    const input = { reason: 'x', until: null };
    expect(await runSanction({ admin }, 'suspendStore', 's1', input)).toEqual({
      kind: 'store',
      store: { id: 's1', name: '망원베이커리', status: 'SUSPENDED' },
    });
    expect(await runSanction({ admin }, 'closeStore', 's1', input)).toMatchObject({
      kind: 'store',
      store: { status: 'CLOSED' },
    });
    expect(await runSanction({ admin }, 'suspendOffer', 'o1', input)).toMatchObject({
      kind: 'offer',
      offer: { title: '식빵 모둠 5종' },
    });
    expect(admin.closeStore).toHaveBeenCalledWith('s1', 'x');
    expect(admin.suspendOffer).toHaveBeenCalledWith('o1', 'x');
  });
});
