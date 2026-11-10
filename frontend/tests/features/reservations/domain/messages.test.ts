import { cancelErrorMessage, reserveErrorMessage } from '@/features/reservations/domain/messages';

describe('오류 문구(서버 message 사용, D-16)', () => {
  it('cancelErrorMessage: 400 CANCELLATION_DEADLINE_PASSED는 서버 message 그대로', () => {
    const message = '취소 가능 시각이 지나 취소·환불할 수 없습니다.';
    expect(cancelErrorMessage({ errorCode: 'CANCELLATION_DEADLINE_PASSED', message })).toBe(
      message,
    );
  });

  it('reserveErrorMessage: OUT_OF_STOCK은 서버 message 그대로', () => {
    expect(reserveErrorMessage({ errorCode: 'OUT_OF_STOCK', message: '재고가 부족합니다.' })).toBe(
      '재고가 부족합니다.',
    );
  });
});
