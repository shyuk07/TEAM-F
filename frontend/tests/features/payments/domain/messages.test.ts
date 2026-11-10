import { payErrorMessage } from '@/features/payments/domain/messages';

describe('payErrorMessage (D-7: 서버 message 사용)', () => {
  it('400 INVALID_POINT_AMOUNT는 서버 message 그대로', () => {
    expect(
      payErrorMessage({ status: 400, errorCode: 'INVALID_POINT_AMOUNT', message: '포인트 초과' }),
    ).toBe('포인트 초과');
  });

  it('409는 error_code와 관계없이 서버 message를 쓴다', () => {
    expect(payErrorMessage({ status: 409, errorCode: 'ANYTHING', message: '이미 결제됨' })).toBe(
      '이미 결제됨',
    );
  });
});
