import { isOwnerPath, roleLabel } from '@/features/auth/domain/user';

describe('roleLabel', () => {
  it.each([
    ['OWNER', '상점주'],
    ['CUSTOMER', '고객'],
    ['ADMIN', '관리자'],
  ] as const)('%s → %s', (role, label) => {
    expect(roleLabel(role)).toBe(label);
  });
});

describe('isOwnerPath', () => {
  it.each([
    ['/owner', true],
    ['/owner/today', true],
    ['/ownerx', false],
    ['/', false],
  ])('%s → %s', (path, expected) => {
    expect(isOwnerPath(path)).toBe(expected);
  });
});
