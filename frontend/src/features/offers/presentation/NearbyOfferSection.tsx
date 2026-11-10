import type { HomeOffers } from '../application/useHomeOffers';
import { OfferCard } from './OfferCard';
import { OfferCardSkeleton } from './OfferCardSkeleton';

// TODO: 임시 문구다(빈 목록(검색어 있음), 오류, 「더 보기」, 더 보기 실패, 위치 칩 라벨).
//   왜: screens.md·content.md에 C1 목록 상태 문구가 없다 (docs/design/frontend/offers.md D-20, D-21, D-23, D-32)
//   언제: 결정 후 (디자인 시스템: content.md C1 문구 확정)
const ERROR_TEXT = '할인 목록을 불러오지 못했어요. 잠시 후 다시 시도해 주세요.';
const RETRY_LABEL = '다시 시도';
const MORE_LABEL = '더 보기';
const MORE_BUSY_LABEL = '처리 중…';
const MORE_FAILED_TEXT = '더 불러오지 못했어요. 다시 시도해 주세요.';

export function NearbyOfferSection({ home }: { home: HomeOffers }) {
  const { list, empty, now } = home;

  if (list.status === 'loading') {
    return (
      <div style={{ display: 'grid', gap: 'var(--s3)' }} aria-busy="true" aria-label="불러오는 중">
        <OfferCardSkeleton />
        <OfferCardSkeleton />
        <OfferCardSkeleton />
      </div>
    );
  }

  if (list.status === 'error') {
    return (
      <div style={{ display: 'grid', gap: 'var(--s2)' }}>
        <div className="warn" role="alert">
          {ERROR_TEXT}
        </div>
        <button
          type="button"
          className="btn sm"
          style={{ justifySelf: 'start' }}
          onClick={list.reload}
        >
          {RETRY_LABEL}
        </button>
      </div>
    );
  }

  if (list.status === 'empty') {
    return (
      <div className="box empty">
        <div className="ic" aria-hidden="true" />
        <b>{empty.title}</b>
        <div className="m">{empty.reason}</div>
        {empty.actionLabel !== null ? (
          <button type="button" className="btn sm" onClick={home.runEmptyAction}>
            {empty.actionLabel}
          </button>
        ) : null}
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gap: 'var(--s3)' }}>
      {list.items.map((item) => (
        <OfferCard key={item.offer.id} item={item} now={now} />
      ))}
      {list.hasMore ? (
        <>
          {list.moreFailed ? <div className="err">{MORE_FAILED_TEXT}</div> : null}
          <button type="button" className="btn" disabled={list.loadingMore} onClick={list.loadMore}>
            {list.loadingMore ? MORE_BUSY_LABEL : MORE_LABEL}
          </button>
        </>
      ) : null}
    </div>
  );
}
