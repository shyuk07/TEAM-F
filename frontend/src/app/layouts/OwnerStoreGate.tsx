// FIXME: 상점이 정지되어도 O1에 정지 안내가 고정되지 않는다. 가드는 O1로 보내기만 한다.
//   왜: O1 화면이 자리 page라 StoreSuspendedNotice를 놓을 곳이 없다 (docs/design/frontend/stores.md §4.4)
//   언제: O1 구현 시, 늦어도 배포 전
export function OwnerStoreGate() {
  return null;
}
