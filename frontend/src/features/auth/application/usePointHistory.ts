import { useCallback, useEffect, useRef, useState } from 'react';
import { SessionStoreToken } from '@/entities/session';
import { useDep } from '@/shared/lib/di';
import type { PointLog } from '../domain/points';
import { loadPoints } from './points';
import { AccountGatewayToken } from './tokens';

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

type Loaded = {
  status: PointHistoryState['status'];
  balance: number | null;
  logs: PointLog[];
  total: number;
  page: number;
};

const INITIAL: Loaded = { status: 'loading', balance: null, logs: [], total: 0, page: 0 };

// 첫 페이지(page 0)를 받고 loadMore()로 다음 페이지를 이어 붙인다. 401은 유스케이스가 세션을 지운다(customer-home.md §3.2).
export function usePointHistory(pageSize: number): PointHistoryState {
  const account = useDep(AccountGatewayToken);
  const session = useDep(SessionStoreToken);
  const [data, setData] = useState<Loaded>(INITIAL);
  const [loadingMore, setLoadingMore] = useState(false);
  const [loadMoreFailed, setLoadMoreFailed] = useState(false);
  const [nonce, setNonce] = useState(0);
  const ctrlRef = useRef<AbortController | null>(null);
  const moreRef = useRef(false);

  useEffect(() => {
    const ctrl = new AbortController();
    ctrlRef.current = ctrl;
    moreRef.current = false;
    loadPoints({ account, session }, { page: 0, size: pageSize }, ctrl.signal).then(
      (p) => {
        if (ctrl.signal.aborted) return;
        setData({
          status: p.logs.length === 0 ? 'empty' : 'success',
          balance: p.balance,
          logs: p.logs,
          total: p.total,
          page: 0,
        });
      },
      () => {
        if (!ctrl.signal.aborted) setData({ ...INITIAL, status: 'error' });
      },
    );
    return () => ctrl.abort();
  }, [account, session, pageSize, nonce]);

  const hasMore = data.status === 'success' && data.logs.length < data.total;

  const loadMore = useCallback(() => {
    const ctrl = ctrlRef.current;
    if (!hasMore || moreRef.current || ctrl === null) return;
    moreRef.current = true;
    setLoadingMore(true);
    setLoadMoreFailed(false);
    const next = data.page + 1;
    loadPoints({ account, session }, { page: next, size: pageSize }, ctrl.signal)
      .then(
        (p) => {
          if (ctrl.signal.aborted) return;
          setData((prev) => {
            const seen = new Set(prev.logs.map((l) => l.id));
            const added = p.logs.filter((l) => !seen.has(l.id));
            return {
              ...prev,
              balance: p.balance,
              logs: [...prev.logs, ...added],
              total: p.total,
              page: next,
            };
          });
        },
        () => {
          if (!ctrl.signal.aborted) setLoadMoreFailed(true);
        },
      )
      .finally(() => {
        if (ctrl.signal.aborted) return;
        moreRef.current = false;
        setLoadingMore(false);
      });
  }, [account, session, pageSize, hasMore, data.page]);

  // 첫 페이지부터 다시(목록 초기화)
  const retry = useCallback(() => {
    setData(INITIAL);
    setLoadingMore(false);
    setLoadMoreFailed(false);
    setNonce((n) => n + 1);
  }, []);

  return {
    status: data.status,
    balance: data.balance,
    logs: data.logs,
    total: data.total,
    hasMore,
    loadingMore,
    loadMoreFailed,
    loadMore,
    retry,
  };
}
