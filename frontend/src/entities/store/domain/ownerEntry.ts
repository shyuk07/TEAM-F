import type { Store } from './store';

// features/auth의 AccountStatus와 같은 값 목록이다. auth를 import하지 않기 위해 자기 합집합으로 둔다(F1).
export type OwnerAccountStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'SUSPENDED' | 'WITHDRAWN';

export type MyStoreLookup =
  | { status: 'loading' }
  | { status: 'none' }
  | { status: 'found'; store: Store }
  | { status: 'error'; errorCode: string; message: string };

export type OwnerEntryDecision = 'loading' | 'error' | 'allow' | 'to-start' | 'to-today';

export type OwnerStartView = 'pending' | 'rejected' | 'open-form' | 'closed' | 'account-blocked';

// TODO: 임시 문구다(상점 조회 실패 문구, 계정 name null 개설 불가 안내 문구). 정본 문구가 정해지면 바꾼다.
//   왜: screens.md·content.md에 해당 문구가 없다 (docs/design/frontend/stores.md D-11, D-21)
//   언제: 결정 후 (디자인 시스템: content.md 문구 확정)
export const MY_STORE_ERROR_FALLBACK_MESSAGE =
  '상점 정보를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.';

export function decideOwnerEntry(input: {
  lookup: MyStoreLookup;
  onStartPage: boolean;
}): OwnerEntryDecision {
  const { lookup, onStartPage } = input;
  if (lookup.status === 'loading') return 'loading';
  if (lookup.status === 'error') return 'error';
  if (lookup.status === 'none') return onStartPage ? 'allow' : 'to-start';
  if (lookup.store.status === 'ACTIVE' || lookup.store.status === 'SUSPENDED') {
    return onStartPage ? 'to-today' : 'allow';
  }
  // found CLOSED: 폐점한 상점의 하위 화면은 쓸 수 없다. O7도 O0로 되돌린다(§3.1 표).
  return onStartPage ? 'allow' : 'to-start';
}

export function ownerStartView(input: {
  accountStatus: OwnerAccountStatus;
  lookup: MyStoreLookup;
}): OwnerStartView | null {
  const { accountStatus, lookup } = input;
  if (lookup.status === 'none') {
    switch (accountStatus) {
      case 'PENDING':
        return 'pending';
      case 'REJECTED':
        return 'rejected';
      case 'APPROVED':
        return 'open-form';
      case 'SUSPENDED':
      case 'WITHDRAWN':
        return 'account-blocked';
    }
  }
  if (lookup.status === 'found' && lookup.store.status === 'CLOSED') return 'closed';
  return null;
}

// TODO: 정지 상점주는 계정도 정지되어 /users/me 403이라 account-blocked 분기에 도달하지 못한다(사용자 Q-6 확정).
//   왜: 분기는 방어용으로 유지. 관리자의 상점 정지가 실제로 계정까지 정지하는지 백엔드 확인이 남아 있다 (docs/design/frontend/stores.md C-1, D-22)
//   언제: 결정 후 (백엔드: 정지 시 계정 정지 실제 동작 확인)
