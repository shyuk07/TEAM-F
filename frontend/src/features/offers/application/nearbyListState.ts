import type { NearbyOffer, NearbyOfferPage } from '../domain/offer';
import { appendPage, hasNextPage } from '../domain/search';

export type NearbyListState = {
  status: 'loading' | 'error' | 'ready';
  key: string;
  items: NearbyOffer[];
  page: number;
  total: number;
  hasMore: boolean;
  loadingMore: boolean;
  moreFailed: boolean;
  error: unknown;
};

export type NearbyListAction =
  | { type: 'queryChanged'; key: string }
  | { type: 'firstLoaded'; key: string; page: NearbyOfferPage }
  | { type: 'firstFailed'; key: string; error: unknown }
  | { type: 'moreRequested' }
  | { type: 'moreLoaded'; key: string; page: NearbyOfferPage }
  | { type: 'moreFailed'; key: string; error: unknown }
  | { type: 'reload' };

export const initialNearbyListState: NearbyListState = {
  status: 'loading',
  key: '',
  items: [],
  page: 0,
  total: 0,
  hasMore: false,
  loadingMore: false,
  moreFailed: false,
  error: null,
};

export function nearbyListReducer(
  state: NearbyListState,
  action: NearbyListAction,
): NearbyListState {
  switch (action.type) {
    case 'queryChanged':
      return { ...initialNearbyListState, key: action.key };
    case 'reload':
      return { ...initialNearbyListState, key: state.key };
    case 'firstLoaded':
      if (action.key !== state.key) return state;
      return {
        ...state,
        status: 'ready',
        items: action.page.items,
        page: action.page.page,
        total: action.page.total,
        hasMore: hasNextPage(action.page),
        loadingMore: false,
        moreFailed: false,
        error: null,
      };
    case 'firstFailed':
      if (action.key !== state.key) return state;
      return { ...state, status: 'error', error: action.error };
    case 'moreRequested':
      if (state.status !== 'ready' || !state.hasMore || state.loadingMore) return state;
      return { ...state, loadingMore: true, moreFailed: false };
    case 'moreLoaded':
      if (action.key !== state.key) return state;
      return {
        ...state,
        items: appendPage(state.items, action.page.items),
        page: action.page.page,
        total: action.page.total,
        hasMore: hasNextPage(action.page),
        loadingMore: false,
        moreFailed: false,
      };
    case 'moreFailed':
      if (action.key !== state.key) return state;
      return { ...state, loadingMore: false, moreFailed: true };
  }
}
