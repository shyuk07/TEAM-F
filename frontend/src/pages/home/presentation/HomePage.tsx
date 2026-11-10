import { useRef, useState, type FormEvent } from 'react';
import { Link, useLocation, useNavigate } from 'react-router';
import { useAuth } from '@/features/auth';
import {
  KEYWORD_MAX_LENGTH,
  LOAD_MORE_LABEL,
  LocationSheet,
  NearbyEmpty,
  OFFERS_LOAD_FAILED_MESSAGE,
  OfferCard,
  OfferCardSkeleton,
  OWNER_APPLY_LINK,
  SEARCH_LABEL,
  SortChips,
  locationChipLabel,
  nextRadius,
  readHomeFilter,
  toHomeSearch,
  useDeviceLocation,
  useNearbyOffers,
  type HomeFilter,
} from '@/features/offers';
import { ROUTES } from '@/shared/lib/routes';
import { useNow } from '@/shared/lib/useNow';

const SKELETON_COUNT = 3;

// C1 홈·주변 할인(비로그인 가능) + C1a 위치·반경 시트(customer-home.md §3.5, wireframe.html:300~339).
// 필터(정렬·반경·검색어)는 URL 쿼리에 두고 바꿀 때 replace한다(D-10). .app·탭 바는 CustomerLayout이 그린다.
export function HomePage() {
  const location = useLocation();
  const navigate = useNavigate();
  const filter = readHomeFilter(location.search);
  const device = useDeviceLocation();
  const hasLocation = device.status === 'ok';
  const offers = useNearbyOffers(filter, device.point, device.status !== 'pending');
  const now = useNow();
  const auth = useAuth().state;
  const [sheetOpen, setSheetOpen] = useState(false);
  const chipRef = useRef<HTMLButtonElement>(null);
  const here = location.pathname + location.search;

  const changeFilter = (next: Partial<HomeFilter>) => {
    navigate({ search: toHomeSearch({ ...filter, ...next }) }, { replace: true });
  };

  const closeSheet = () => {
    setSheetOpen(false);
    chipRef.current?.focus();
  };

  const onSearch = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const value = new FormData(e.currentTarget).get('q');
    // 지운 뒤 제출하면 검색 해제(readHomeFilter와 같이 앞뒤 공백을 뺀다).
    changeFilter({ keyword: typeof value === 'string' ? value.trim() : '' });
  };

  return (
    <>
      <div className="bar">
        <h1 className="logo">마감직전</h1>
        <button
          type="button"
          className={sheetOpen ? 'chip on' : 'chip'}
          ref={chipRef}
          aria-haspopup="dialog"
          aria-expanded={sheetOpen}
          onClick={() => setSheetOpen(true)}
        >
          {locationChipLabel(hasLocation, filter.radiusKm)}
        </button>
        <span className="sp" />
        {auth.status === 'anonymous' ? (
          // entry 없이 넘겨 A1에 진입 안내 줄이 없다(screens.md A1, D-18).
          <Link className="link" to={ROUTES.login} state={{ from: here }}>
            로그인
          </Link>
        ) : null}
      </div>
      {sheetOpen ? (
        <div
          className="dim"
          onClick={(e) => {
            if (e.target === e.currentTarget) closeSheet();
          }}
        >
          <LocationSheet
            hasLocation={hasLocation}
            locating={device.status === 'pending'}
            radiusKm={filter.radiusKm}
            onUseCurrentLocation={device.request}
            onApply={(radiusKm) => {
              changeFilter({ radiusKm });
              closeSheet();
            }}
            onClose={closeSheet}
          />
        </div>
      ) : (
        <div className="body">
          <form role="search" onSubmit={onSearch}>
            {/* 「상품명 검색」은 wireframe.html:305, 최대 길이는 API keyword 100자(catalog.md §8) */}
            <input
              key={filter.keyword}
              className="in"
              type="search"
              name="q"
              aria-label={SEARCH_LABEL}
              placeholder={SEARCH_LABEL}
              maxLength={KEYWORD_MAX_LENGTH}
              defaultValue={filter.keyword}
            />
          </form>
          <SortChips
            value={filter.sort}
            hasLocation={hasLocation}
            onChange={(sort) => changeFilter({ sort })}
          />
          <div aria-busy={offers.status === 'loading'}>
            {offers.status === 'loading'
              ? Array.from({ length: SKELETON_COUNT }, (_, i) => <OfferCardSkeleton key={i} />)
              : null}
            {offers.status === 'error' ? (
              <>
                <div className="warn" role="alert">
                  {OFFERS_LOAD_FAILED_MESSAGE}
                </div>
                <button type="button" className="btn sm" onClick={offers.retry}>
                  다시 시도
                </button>
              </>
            ) : null}
            {offers.status === 'empty' ? (
              <NearbyEmpty
                action={hasLocation ? nextRadius(filter.radiusKm) : null}
                onAction={(radiusKm) => changeFilter({ radiusKm })}
              />
            ) : null}
            {offers.status === 'success'
              ? offers.items.map((item) => <OfferCard key={item.offer.id} item={item} now={now} />)
              : null}
          </div>
          {offers.loadMoreFailed ? (
            <div className="warn" role="alert">
              {OFFERS_LOAD_FAILED_MESSAGE}
            </div>
          ) : null}
          {offers.hasMore ? (
            <button
              type="button"
              className="link"
              aria-disabled={offers.loadingMore ? 'true' : undefined}
              onClick={() => {
                if (!offers.loadingMore) offers.loadMore();
              }}
            >
              {offers.loadingMore ? '처리 중…' : LOAD_MORE_LABEL}
            </button>
          ) : null}
        </div>
      )}
      {auth.status === 'anonymous' ? (
        // 「로그인」과 같이 비로그인일 때만(세션 확인 중 제외). 탭 바 바로 위 고정 위치(wireframe.html:320, screens.md C1, D-18).
        <Link className="link" style={{ padding: 'var(--s2)' }} to={ROUTES.ownerSignup}>
          {OWNER_APPLY_LINK}
        </Link>
      ) : null}
    </>
  );
}
