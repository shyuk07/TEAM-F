// 로딩 카드 뼈대(wireframe.html:542, E1). 읽을 내용이 없어 보조 기술에는 숨긴다.
export function OfferCardSkeleton() {
  return (
    <div className="card" aria-hidden="true">
      <div className="sk" style={{ height: 76 }} />
      <div style={{ display: 'grid', gap: 'var(--s2)' }}>
        <div className="sk" style={{ width: '50%' }} />
        <div className="sk" style={{ width: '80%' }} />
        <div className="sk" style={{ width: '40%' }} />
      </div>
    </div>
  );
}
