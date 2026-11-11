import { describe, expect, it } from 'vitest';
import { readErrorInfo } from '@/shared/lib/errorInfo';

describe('shared/lib/errorInfo.readErrorInfo', () => {
  it('status·errorCode가 있는 객체는 그대로 돌려준다(message 없으면 빈 문자열)', () => {
    expect(readErrorInfo({ status: 404, errorCode: 'NOT_FOUND' })).toEqual({
      status: 404,
      errorCode: 'NOT_FOUND',
      message: '',
    });
    expect(
      readErrorInfo({ status: 409, errorCode: 'RESERVATION_CLOSED', message: '마감' }),
    ).toEqual({ status: 409, errorCode: 'RESERVATION_CLOSED', message: '마감' });
  });

  it.each([
    ['null이면', null],
    ['문자열이면', '오류'],
    ['status 없는 객체면', { errorCode: 'NOT_FOUND' }],
  ])('%s {status:0, errorCode:UNKNOWN, message:""}를 돌려준다', (_label, value) => {
    expect(readErrorInfo(value)).toEqual({ status: 0, errorCode: 'UNKNOWN', message: '' });
  });
});
