import {
  canSaveProfile,
  isNameLocked,
  profileFormOf,
  profilePatch,
  type ProfileForm,
  type ProfilePatch,
} from '@/features/auth/domain/profileInput';
import type { User } from '@/features/auth/domain/user';
import { adminUser, customerUser, legacyCustomerUser, ownerUser } from '../fakes/users';

const customer: User = { ...customerUser, name: '김고객', phone: '010-1' };
const owner: User = { ...ownerUser, name: '망원베이커리', phone: '010-1' };

describe('isNameLocked', () => {
  it.each<[string, User, boolean]>([
    ['OWNER', ownerUser, true],
    ['CUSTOMER', customerUser, false],
    ['ADMIN', adminUser, false],
  ])('%s → %s', (_name, user, expected) => {
    expect(isNameLocked(user)).toBe(expected);
  });
});

describe('profileFormOf', () => {
  it('name이 null이면 빈 문자열이다', () => {
    expect(profileFormOf({ ...customer, name: null })).toEqual({ name: '', phone: '010-1' });
  });
});

describe('profilePatch', () => {
  it.each<[string, User, ProfileForm, ProfilePatch]>([
    ['그대로', customer, { name: '김고객', phone: '010-1' }, {}],
    ['전화 변경', customer, { name: '김고객', phone: '010-2' }, { phone: '010-2' }],
    ['이름 변경', customer, { name: '박고객', phone: '010-1' }, { name: '박고객' }],
    [
      '둘 다 변경',
      customer,
      { name: '박고객', phone: '010-2' },
      { name: '박고객', phone: '010-2' },
    ],
    ['앞뒤 공백만 다름(trim 뒤 같음)', customer, { name: '김고객', phone: ' 010-1 ' }, {}],
    ['상점주 이름 변경(잠김)', owner, { name: '다른상호', phone: '010-1' }, {}],
    ['상점주 전화 변경', owner, { name: '망원베이커리', phone: '010-2' }, { phone: '010-2' }],
  ])('%s', (_name, user, form, expected) => {
    expect(profilePatch(user, form)).toEqual(expected);
  });
});

describe('canSaveProfile', () => {
  it.each<[string, User, ProfileForm, boolean]>([
    ['바뀐 값 없음', customer, { name: '김고객', phone: '010-1' }, false],
    ['전화를 공백으로', customer, { name: '김고객', phone: '  ' }, false],
    ['전화 변경', customer, { name: '김고객', phone: '010-2' }, true],
    [
      '이름이 null인 고객이 전화만 변경(REQ-23)',
      { ...legacyCustomerUser, phone: '010-1' },
      { name: '', phone: '010-2' },
      false,
    ],
    [
      '이름이 null인 ADMIN이 전화만 변경(관리자 제외)',
      { ...adminUser, name: null, phone: '010-1' },
      { name: '', phone: '010-2' },
      true,
    ],
  ])('%s → %s', (_name, user, form, expected) => {
    expect(canSaveProfile(user, form)).toBe(expected);
  });
});
