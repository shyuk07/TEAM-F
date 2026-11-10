export function OfferCardSkeleton() {
  return (
    <div className="card">
      <div className="ph" aria-hidden="true" />
      <div style={{ display: 'grid', gap: 'var(--s2)' }}>
        <div className="sk" style={{ width: '40%' }} />
        <div className="sk" style={{ width: '70%' }} />
        <div className="sk" style={{ width: '55%' }} />
      </div>
    </div>
  );
}
