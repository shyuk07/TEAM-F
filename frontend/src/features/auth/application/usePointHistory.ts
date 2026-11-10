import type { PointLog } from '../domain/points';

export type PointHistoryState = {
  status: 'loading' | 'success' | 'empty' | 'error';
  balance: number | null;
  logs: PointLog[];
  total: number;
  hasMore: boolean;
  loadingMore: boolean;
  loadMoreFailed: boolean;
  loadMore(): void;
  retry(): void;
};

export function usePointHistory(pageSize: number): PointHistoryState {
  void pageSize;
  throw new Error('not implemented: usePointHistory');
}
