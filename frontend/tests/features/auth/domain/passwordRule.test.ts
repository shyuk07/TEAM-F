import {
  checkPassword,
  utf8ByteLength,
  type PasswordCheck,
} from '@/features/auth/domain/passwordRule';

describe('checkPassword', () => {
  it.each<[string, string, PasswordCheck]>([
    ['빈 문자열', '', 'empty'],
    ['공백 3칸(공백 검사가 길이보다 먼저)', '   ', 'blank'],
    ['공백 8칸', '        ', 'blank'],
    ['7자', '1234567', 'tooShort'],
    ['8자', '12345678', 'ok'],
    ['앞 공백 포함 8자(trim하지 않음)', ' abcdefg', 'ok'],
    ['ASCII 72바이트', 'a'.repeat(72), 'ok'],
    ['ASCII 73바이트', 'a'.repeat(73), 'tooLong'],
    ['한글 24자(72바이트)', '가'.repeat(24), 'ok'],
    ['한글 25자(75바이트)', '가'.repeat(25), 'tooLong'],
    ['이모지 7개(코드 포인트 7, UTF-16 14)', '😀'.repeat(7), 'tooShort'],
    ['이모지 18개(72바이트)', '😀'.repeat(18), 'ok'],
    ['이모지 19개(76바이트)', '😀'.repeat(19), 'tooLong'],
  ])('%s → %s', (_name, password, expected) => {
    expect(checkPassword(password)).toBe(expected);
  });
});

describe('utf8ByteLength', () => {
  it.each<[string, number]>([
    ['', 0],
    ['a', 1],
    ['é', 2],
    ['가', 3],
    ['😀', 4],
  ])('%j → %i바이트', (text, expected) => {
    expect(utf8ByteLength(text)).toBe(expected);
  });
});
