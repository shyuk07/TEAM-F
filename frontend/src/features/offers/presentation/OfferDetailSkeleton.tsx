// 로딩 중 이미지 자리 + 줄 3개(offers.md §3.4).
export function OfferDetailSkeleton() {
  return (
    <div className="body" aria-busy="true">
      <div className="ph" style={{ minHeight: 170 }} aria-hidden="true" />
      <div className="sk"></div>
      <div className="sk"></div>
      <div className="sk"></div>
    </div>
  );
}
