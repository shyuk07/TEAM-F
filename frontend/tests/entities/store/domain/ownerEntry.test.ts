import { describe, expect, it } from 'vitest';
import { decideOwnerEntry, ownerStartView } from '@/entities/store';
import { activeStore, closedStore, suspendedStore } from '../fakes/stores';

describe('entities/store domain decideOwnerEntry (설계안 §3.1 표)', () => {
  it.each([
    ['loading 시작', { lookup: { status: 'loading' }, onStartPage: true }, 'loading'],
    ['loading · 시작 화면 아님', { lookup: { status: 'loading' }, onStartPage: false }, 'loading'],
    [
      'error · 시작 화면',
      { lookup: { status: 'error', errorCode: 'X', message: 'm' }, onStartPage: true },
      'error',
    ],
    [
      'error · 시작 화면 아님',
      { lookup: { status: 'error', errorCode: 'X', message: 'm' }, onStartPage: false },
      'error',
    ],
    ['none · 시작 화면', { lookup: { status: 'none' }, onStartPage: true }, 'allow'],
    ['none · 시작 화면 아님', { lookup: { status: 'none' }, onStartPage: false }, 'to-start'],
    [
      'ACTIVE · 시작 화면',
      { lookup: { status: 'found', store: activeStore }, onStartPage: true },
      'to-today',
    ],
    [
      'ACTIVE · 시작 화면 아님',
      { lookup: { status: 'found', store: activeStore }, onStartPage: false },
      'allow',
    ],
    [
      'SUSPENDED · 시작 화면',
      { lookup: { status: 'found', store: suspendedStore }, onStartPage: true },
      'to-today',
    ],
    [
      'SUSPENDED · 시작 화면 아님',
      { lookup: { status: 'found', store: suspendedStore }, onStartPage: false },
      'allow',
    ],
    [
      'CLOSED · 시작 화면',
      { lookup: { status: 'found', store: closedStore }, onStartPage: true },
      'allow',
    ],
    [
      'CLOSED · 시작 화면 아님',
      { lookup: { status: 'found', store: closedStore }, onStartPage: false },
      'to-start',
    ],
  ] as const)('%s → %s', (_label, input, expected) => {
    expect(decideOwnerEntry(input)).toBe(expected);
  });
});

describe('entities/store domain ownerStartView (설계안 §3.1 표)', () => {
  it.each([
    ['PENDING', 'pending'],
    ['REJECTED', 'rejected'],
    ['APPROVED', 'open-form'],
    ['SUSPENDED', 'account-blocked'],
    ['WITHDRAWN', 'account-blocked'],
  ] as const)('상점 없음 + 계정 %s → %s', (accountStatus, expected) => {
    expect(ownerStartView({ accountStatus, lookup: { status: 'none' } })).toBe(expected);
  });

  it('상점 CLOSED면 계정 상태 무관하게 closed다', () => {
    expect(
      ownerStartView({
        accountStatus: 'APPROVED',
        lookup: { status: 'found', store: closedStore },
      }),
    ).toBe('closed');
  });

  it.each([
    ['ACTIVE', { status: 'found', store: activeStore } as const],
    ['SUSPENDED', { status: 'found', store: suspendedStore } as const],
  ])('상점 %s면 null이다', (_label, lookup) => {
    expect(ownerStartView({ accountStatus: 'APPROVED', lookup })).toBeNull();
  });

  it.each([
    ['loading', { status: 'loading' } as const],
    ['error', { status: 'error', errorCode: 'X', message: 'm' } as const],
  ])('조회가 %s면 null이다', (_label, lookup) => {
    expect(ownerStartView({ accountStatus: 'APPROVED', lookup })).toBeNull();
  });
});
