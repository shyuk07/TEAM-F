// 포인트 내역 로딩 뼈대(Skeleton README: 스피너 대신 실제 행 모양)
export function PointLogSkeleton({ rows }: { rows: number }) {
  return (
    <div className="list" aria-busy="true">
      {Array.from({ length: rows }, (_, i) => (
        <div className="li" key={i}>
          <div style={{ display: 'grid', gap: 'var(--s2)', flex: 1 }}>
            <div className="sk" style={{ width: '30%' }} />
            <div className="sk" style={{ width: '50%' }} />
          </div>
          <div className="sk" style={{ width: '20%' }} />
        </div>
      ))}
    </div>
  );
}
