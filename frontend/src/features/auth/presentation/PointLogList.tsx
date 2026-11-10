import { formatPointDelta, pointLogMeta, pointTypeLabel, type PointLog } from '../domain/points';

// 포인트 내역 행(ListRow README): 종류(굵게) + 날짜·잔액(muted) / 오른쪽 금액.
// TODO: 포인트 내역 사유(결제·환불·이벤트 보상)를 보여 주지 않는다.
//   왜: 포인트 내역 응답에 사유 필드가 없다 (customer-home.md C-5)
//   언제: 결정 후 (백엔드: point_log 사유)
export function PointLogList({ logs, variant }: { logs: PointLog[]; variant: 'short' | 'full' }) {
  return (
    <div className="list">
      {logs.map((log) => (
        <div className="li" key={log.id}>
          <div>
            <b>{pointTypeLabel(log.type)}</b>
            <div className="m">{pointLogMeta(log, variant)}</div>
          </div>
          <b>{formatPointDelta(log.amount)}</b>
        </div>
      ))}
    </div>
  );
}
