// TODO: 계정 버튼을 눌러도 아무 동작이 없다. O8(계정 메뉴)로 이동하게 연결한다.
//   왜: O8은 auth 영역 몫이라 이번 범위 밖 (docs/design/frontend/app-shell.md D-4, 사용자: 계정 행은 자리만)
//   언제: auth 구현 시
export function OwnerAccountButton() {
  return (
    <button type="button" className="acct">
      계정
    </button>
  );
}
