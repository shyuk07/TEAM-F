// TODO: 자리 page가 화면 ID만 표시한다. 정식 page(pages/*)로 교체하고 이 파일을 지운다.
//   왜: 문구 정본이 없는 개발용 표기다 (docs/design/frontend/app-shell.md D-8, D-15)
//   언제: O1 구현 시, O2 구현 시, O3 구현 시, O4 구현 시, O6 구현 시, O11 구현 시 (각 화면의 자리 page를 교체)
import { useParams } from 'react-router';
import { OwnerAccountButton, OwnerTopNav } from '@/widgets/owner-nav';

function OwnerPlaceholder({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <>
      <div className="bar">
        <span className="logo">{title}</span>
        <span className="sp"></span>
        <OwnerTopNav />
        <OwnerAccountButton />
      </div>
      <div className="body">
        <h1>{title}</h1>
        {children}
      </div>
    </>
  );
}

export function OwnerTodayPlaceholder() {
  return <OwnerPlaceholder title="O1 오늘" />;
}

export function OwnerOffersPlaceholder() {
  return <OwnerPlaceholder title="O2 할인" />;
}

export function OwnerOfferNewPlaceholder() {
  return <OwnerPlaceholder title="O3 할인 등록" />;
}

export function OwnerStorePlaceholder() {
  return <OwnerPlaceholder title="O4 매장" />;
}

export function OwnerProductNewPlaceholder() {
  return <OwnerPlaceholder title="O6 상품 등록" />;
}

export function OwnerProductEditPlaceholder() {
  const { productId } = useParams();
  return (
    <OwnerPlaceholder title="O11 상품 수정">
      <p>{productId}</p>
    </OwnerPlaceholder>
  );
}

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
