import { validateDeactivate } from '@/features/offers';

describe('validateDeactivate', () => {
  it('사유가 빈 문자열이면 reason-empty', () => {
    expect(validateDeactivate({ reason: '' })).toBe('reason-empty');
  });
  it('사유가 공백만 있으면 reason-empty', () => {
    expect(validateDeactivate({ reason: '   ' })).toBe('reason-empty');
  });
  it('1자 이상 200자 이하면 null', () => {
    expect(validateDeactivate({ reason: '재고 소진' })).toBeNull();
    expect(validateDeactivate({ reason: 'a'.repeat(200) })).toBeNull();
  });
  it('201자 이상이면 reason-too-long', () => {
    expect(validateDeactivate({ reason: 'a'.repeat(201) })).toBe('reason-too-long');
  });
});
