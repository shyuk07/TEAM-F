import {
  canSubmitSignup,
  nameLabel,
  readSignupRole,
  toSignupInput,
  type SignupForm,
  type SignupRole,
} from '@/features/auth/domain/signupInput';

const validCustomer: SignupForm = {
  role: 'CUSTOMER',
  name: '홍길동',
  email: 'a@b.c',
  password: 'pw123456',
  phone: '010-1',
};

describe('readSignupRole', () => {
  it.each<[string, SignupRole]>([
    ['?role=owner', 'OWNER'],
    ['', 'CUSTOMER'],
    ['?role=OWNER', 'CUSTOMER'],
    ['?role=admin', 'CUSTOMER'],
    ['?role=customer', 'CUSTOMER'],
    ['?x=1&role=owner', 'OWNER'],
  ])('%j → %s', (search, expected) => {
    expect(readSignupRole(search)).toBe(expected);
  });
});

describe('canSubmitSignup', () => {
  it.each<[string, Partial<SignupForm>, boolean]>([
    ['모두 유효한 고객 폼', {}, true],
    ['모두 유효한 상점주 폼', { role: 'OWNER' }, true],
    ['이름 빈 값', { name: '' }, false],
    ['이름 공백만', { name: '  ' }, false],
    ['이메일 공백만', { email: ' ' }, false],
    ['전화번호 빈 값', { phone: '' }, false],
    ['비밀번호 7자', { password: '1234567' }, false],
    ['비밀번호 공백 8칸', { password: '        ' }, false],
    ['비밀번호 73바이트', { password: 'a'.repeat(73) }, false],
  ])('%s → %s', (_name, override, expected) => {
    expect(canSubmitSignup({ ...validCustomer, ...override })).toBe(expected);
  });
});

describe('toSignupInput', () => {
  it('이름·이메일·전화번호의 앞뒤 공백을 지운다', () => {
    const input = toSignupInput({
      ...validCustomer,
      name: ' 홍길동 ',
      email: ' a@b.c ',
      phone: ' 010 ',
    });
    expect(input).toMatchObject({ name: '홍길동', email: 'a@b.c', phone: '010' });
  });

  it('비밀번호는 공백을 포함해 그대로 둔다', () => {
    expect(toSignupInput({ ...validCustomer, password: ' pw123456 ' }).password).toBe(' pw123456 ');
  });

  it('role은 그대로 둔다', () => {
    expect(toSignupInput({ ...validCustomer, role: 'OWNER' }).role).toBe('OWNER');
  });
});

describe('nameLabel', () => {
  it.each<[SignupRole, string]>([
    ['CUSTOMER', '이름 *'],
    ['OWNER', '상호(상점명으로 쓰임) *'],
  ])('%s → %s', (role, expected) => {
    expect(nameLabel(role)).toBe(expected);
  });
});
