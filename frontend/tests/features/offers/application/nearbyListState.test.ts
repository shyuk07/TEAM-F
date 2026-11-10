import {
  initialNearbyListState,
  nearbyListReducer,
  type NearbyListAction,
  type NearbyListState,
} from '@/features/offers/application/nearbyListState';
import { manyOffers, pageOf } from '../fakes/offers';

function run(actions: NearbyListAction[], from: NearbyListState = initialNearbyListState) {
  return actions.reduce(nearbyListReducer, from);
}

const firstPage = pageOf(manyOffers(20, 'a'), 1, 20, 45);

function readyState(): NearbyListState {
  return run([
    { type: 'queryChanged', key: 'k1' },
    { type: 'firstLoaded', key: 'k1', page: firstPage },
  ]);
}

describe('nearbyListReducer', () => {
  it('queryChanged → 로딩, 목록·쪽·오류·더 보기 상태 초기화', () => {
    const failed = run(
      [{ type: 'moreRequested' }, { type: 'moreFailed', key: 'k1', error: new Error('x') }],
      readyState(),
    );
    const next = nearbyListReducer(failed, { type: 'queryChanged', key: 'k2' });
    expect(next).toMatchObject({
      status: 'loading',
      key: 'k2',
      items: [],
      page: 0,
      hasMore: false,
      loadingMore: false,
      moreFailed: false,
      error: null,
    });
  });

  it('firstLoaded → ready, items, hasMore 계산', () => {
    const state = readyState();
    expect(state.status).toBe('ready');
    expect(state.items).toEqual(firstPage.items);
    expect(state.page).toBe(1);
    expect(state.total).toBe(45);
    expect(state.hasMore).toBe(true);
  });

  it('firstLoaded의 key가 현재와 다르면 무시한다(늦게 온 이전 요청)', () => {
    const loading = nearbyListReducer(initialNearbyListState, { type: 'queryChanged', key: 'k2' });
    const next = nearbyListReducer(loading, { type: 'firstLoaded', key: 'k1', page: firstPage });
    expect(next).toEqual(loading);
  });

  it('firstFailed → error', () => {
    const err = new Error('boom');
    const loading = nearbyListReducer(initialNearbyListState, { type: 'queryChanged', key: 'k1' });
    const next = nearbyListReducer(loading, { type: 'firstFailed', key: 'k1', error: err });
    expect(next.status).toBe('error');
    expect(next.error).toBe(err);
  });

  it('moreRequested 정상 → loadingMore', () => {
    const next = nearbyListReducer(readyState(), { type: 'moreRequested' });
    expect(next.loadingMore).toBe(true);
    expect(next.moreFailed).toBe(false);
  });

  it('moreRequested가 hasMore false면 변화 없음', () => {
    const last = run([
      { type: 'queryChanged', key: 'k1' },
      { type: 'firstLoaded', key: 'k1', page: pageOf(manyOffers(2, 'a'), 1, 20, 2) },
    ]);
    expect(last.hasMore).toBe(false);
    expect(nearbyListReducer(last, { type: 'moreRequested' })).toEqual(last);
  });

  it('moreRequested가 loadingMore 중이면 변화 없음', () => {
    const loadingMore = nearbyListReducer(readyState(), { type: 'moreRequested' });
    expect(nearbyListReducer(loadingMore, { type: 'moreRequested' })).toEqual(loadingMore);
  });

  it('moreLoaded → 중복을 빼고 이어 붙인다', () => {
    const second = pageOf([...manyOffers(2, 'a').slice(0, 1), ...manyOffers(19, 'b')], 2, 20, 45);
    const next = run(
      [{ type: 'moreRequested' }, { type: 'moreLoaded', key: 'k1', page: second }],
      readyState(),
    );
    expect(next.items).toHaveLength(20 + 19);
    expect(new Set(next.items.map((i) => i.offer.id)).size).toBe(39);
    expect(next.page).toBe(2);
    expect(next.hasMore).toBe(true);
    expect(next.loadingMore).toBe(false);
  });

  it('moreFailed → 목록 유지, moreFailed true', () => {
    const next = run(
      [{ type: 'moreRequested' }, { type: 'moreFailed', key: 'k1', error: new Error('x') }],
      readyState(),
    );
    expect(next.items).toEqual(firstPage.items);
    expect(next.loadingMore).toBe(false);
    expect(next.moreFailed).toBe(true);
  });

  it('reload → queryChanged와 같은 효과(key 유지, 로딩, 목록 비움)', () => {
    const next = nearbyListReducer(readyState(), { type: 'reload' });
    expect(next).toMatchObject({ status: 'loading', key: 'k1', items: [], page: 0 });
  });
});
