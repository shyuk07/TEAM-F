// TODO: 자리 page가 화면 ID만 표시한다. 정식 page(pages/*)로 교체하고 이 파일을 지운다.
//   왜: 문구 정본이 없는 개발용 표기다 (docs/design/frontend/app-shell.md D-8, D-15)
//   언제: C5 구현 시 (각 화면의 자리 page를 교체)

// 고객 자리 page는 .bar·.body만 그린다(.app·프레임·탭 바는 CustomerLayout, customer-home.md §4).
export function ReservationsPlaceholder() {
  return (
    <>
      <div className="bar">
        <h1 className="logo">C5 내 예약</h1>
        <span className="sp"></span>
      </div>
      <div className="body"></div>
    </>
  );
}
