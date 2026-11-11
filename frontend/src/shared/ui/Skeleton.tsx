export function Skeleton() {
  return (
    <div className="card" aria-hidden="true">
      <div className="sk" style={{ height: 76 }} />
      <div style={{ display: 'grid', gap: 8 }}>
        <div className="sk" style={{ width: '50%' }} />
        <div className="sk" style={{ width: '80%' }} />
        <div className="sk" style={{ width: '40%' }} />
      </div>
    </div>
  );
}
