import { AppBar } from '@/shared/ui';
import { ownerStartView, useMyStore } from '@/entities/store';
import { useAuth } from '@/features/auth';
import { StoreOpenForm, StoreStartNotice } from '@/features/stores';
import { OwnerLogoutLink } from '@/widgets/owner-nav';

// TODO: 임시 문구다(계정 name null 개설 불가 안내 문구). 정본 문구가 정해지면 바꾼다.
//   왜: screens.md·content.md에 해당 문구가 없다 (docs/design/frontend/stores.md D-21)
//   언제: 결정 후 (디자인 시스템: content.md 문구 확정)
export function OwnerStartPage() {
  const { state } = useAuth();
  const { lookup } = useMyStore();

  const view =
    state.status === 'authenticated'
      ? ownerStartView({ accountStatus: state.user.status, lookup })
      : null;

  // OwnerLayout이 이미 .app을 그리므로 page는 조각이다(stores.md §5).
  return (
    <>
      <AppBar logo title="마감직전 상점주" right={<OwnerLogoutLink />} />
      {view === 'open-form' && state.status === 'authenticated' ? (
        <StoreOpenForm ownerName={state.user.name ?? ''} />
      ) : null}
      {view !== null && view !== 'open-form' ? <StoreStartNotice view={view} /> : null}
    </>
  );
}
