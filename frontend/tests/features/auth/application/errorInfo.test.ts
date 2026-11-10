import { readErrorInfo } from '@/features/auth/application/errorInfo';
import { ApiError } from '@/shared/api/error';

// 회귀 고정용: ApiError가 필드명을 바꾸면 UNKNOWN으로 떨어지는 것을 잡는다.
describe('readErrorInfo', () => {
  it('실제 ApiError에서 status·errorCode·message를 읽는다', () => {
    expect(readErrorInfo(new ApiError(401, 'UNAUTHORIZED', '인증 필요'))).toEqual({
      status: 401,
      errorCode: 'UNAUTHORIZED',
      message: '인증 필요',
    });
  });

  it.each([new Error('x'), null])('%j는 UNKNOWN이다', (e) => {
    expect(readErrorInfo(e)).toEqual({ status: 0, errorCode: 'UNKNOWN', message: '' });
  });
});
