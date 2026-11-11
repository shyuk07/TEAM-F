import { AppBar } from '@/shared/ui';
import { ownerStartView, type OwnerStartView, useMyStore } from '@/entities/store';
import { useAuth } from '@/features/auth';
import { StoreOpenForm, StoreStartNotice } from '@/features/stores';
import { OwnerLogoutLink } from '@/widgets/owner-nav';

// TODO: 임시 문구다(계정 name null 개설 불가 안내 문구). 정본 문구가 정해지면 바꾼다.
//   왜: screens.md·content.md에 해당 문구가 없다 (docs/design/frontend/stores.md D-21)
//   언제: 결정 후 (디자인 시스템: content.md 문구 확정)
export function OwnerStartPage() {
  const { state } = useAuth();
  const { lookup } = useMyStore();

  const authenticated = state.status === 'authenticated';
  const view = authenticated ? ownerStartView({ accountStatus: state.user.status, lookup }) : null;
  // 상점 개설 화면에서만 쓴다. view가 open-form이면 authenticated가므로 여기서 안전하게 뽑힌다.
  const ownerName = authenticated ? (state.user.name ?? '') : '';

  // OwnerLayout이 이미 .app을 그리므로 page는 조각이다(stores.md §5).
  return (
    <>
      <AppBar logo title="마감직전 상점주" right={<OwnerLogoutLink />} />
      {renderView(view, ownerName)}
    </>
  );
}

// O0 단일 화면: 개설 대기·거절·폐점 등은 안내 박스, 개설 가능하면 개설 폼 하나를 그린다.
function renderView(view: OwnerStartView | null, ownerName: string) {
  if (view === null) return null;
  if (view === 'open-form') return <StoreOpenForm ownerName={ownerName} />;
  return <StoreStartNotice view={view} />;
}
