import { formatDistance, salesCountdown } from '../domain/offerFormat';
import { EARLIEST_SALES_END_LABEL, storeOfferCountText } from '../domain/offerMessages';
import type { StoreGroup } from '../domain/storeGroup';
import { OfferCard } from './OfferCard';

const SALES_END_PREFIX = '판매 마감 ';
const HEAD_STYLE = { width: '100%', textAlign: 'left' } as const;

// 가장 빠른 마감까지 남은 시간(「2시간 전」). 지났으면 「판매 종료」.
function earliestEndText(end: Date, now: Date): string {
  const countdown = salesCountdown(end, now);
  return countdown === null ? '판매 종료' : countdown.replace(SALES_END_PREFIX, '');
}

// 가게 묶음 카드(와이어프레임 밖 기능, 사용자 승인). 머리 버튼을 누르면 그 가게 OfferCard 목록을 펼친다.
export function StoreGroupCard({
  group,
  now,
  expanded,
  onToggle,
}: {
  group: StoreGroup;
  now: Date;
  expanded: boolean;
  onToggle(): void;
}) {
  const distance = formatDistance(group.distanceKm);
  return (
    <div className="box">
      <button type="button" style={HEAD_STYLE} aria-expanded={expanded} onClick={onToggle}>
        <div className="t">{group.storeName}</div>
        <div className="m">
          {storeOfferCountText(group.offers.length)}
          {distance === null ? null : ` · ${distance}`}
        </div>
        <div className="m">
          {`${EARLIEST_SALES_END_LABEL} `}
          <span className="cd">{earliestEndText(group.earliestSalesEnd, now)}</span>
        </div>
      </button>
      {expanded
        ? group.offers.map((item) => <OfferCard key={item.offer.id} item={item} now={now} />)
        : null}
    </div>
  );
}
