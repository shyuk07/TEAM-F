import {
  initialNearbyListState,
  nearbyListReducer,
  type NearbyListState,
} from '@/features/offers/application/nearbyListState';
import { manyOffers, pageOf } from '../fakes/offers';

function readyOnK2(): NearbyListState {
  return [
    { type: 'queryChanged', key: 'k1' },
    { type: 'firstLoaded', key: 'k1', page: pageOf(manyOffers(20, 'a'), 1, 20, 45) },
    { type: 'queryChanged', key: 'k2' },
    { type: 'firstLoaded', key: 'k2', page: pageOf(manyOffers(20, 'b'), 1, 20, 45) },
    { type: 'moreRequested' },
  ].reduce(
    (s, a) => nearbyListReducer(s, a as Parameters<typeof nearbyListReducer>[1]),
    initialNearbyListState,
  );
}

describe('nearbyListReducer key 불일치 가드', () => {
  it('질의가 바뀐 뒤 늦게 온 이전 key의 moreLoaded는 상태를 바꾸지 않는다', () => {
    const state = readyOnK2();
    const next = nearbyListReducer(state, {
      type: 'moreLoaded',
      key: 'k1',
      page: pageOf(manyOffers(20, 'c'), 2, 20, 45),
    });
    expect(next).toEqual(state);
  });

  it('질의가 바뀐 뒤 늦게 온 이전 key의 moreFailed는 상태를 바꾸지 않는다', () => {
    const state = readyOnK2();
    const next = nearbyListReducer(state, { type: 'moreFailed', key: 'k1', error: new Error('x') });
    expect(next).toEqual(state);
  });
});
