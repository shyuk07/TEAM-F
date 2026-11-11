import { useCallback, useEffect, useState } from 'react';
import { useDep } from '@/shared/lib/di';
import type { OfferDetail } from '../domain/offerDetail';
import { OfferRepositoryToken } from './tokens';

export type OfferDetailState = {
  status: 'loading' | 'success' | 'notFound' | 'error';
  detail: OfferDetail | null;
  retry(): void;
};

// 받은 결과는 어느 요청(key)의 것인지와 함께 둔다. key가 지금 요청과 다르면 loading으로 본다.
type Loaded = { key: string; status: 'success' | 'notFound' | 'error'; detail: OfferDetail | null };

// 404(없음·정지)와 400(잘못된 id)은 「없음」, 그 밖은 「오류」(offers.md §3.4, D-13).
// shared/api의 ApiError를 application에서 import할 수 없어(F5) status만 구조로 읽는다.
function isNotFound(e: unknown): boolean {
  const status =
    typeof e === 'object' && e !== null && 'status' in e ? (e as { status: unknown }).status : null;
  return status === 404 || status === 400;
}

export function useOfferDetail(offerId: string): OfferDetailState {
  const repo = useDep(OfferRepositoryToken);
  const [attempt, setAttempt] = useState(0);
  const [loaded, setLoaded] = useState<Loaded | null>(null);
  const key = JSON.stringify([offerId, attempt]);

  useEffect(() => {
    const ctrl = new AbortController();
    repo.findById(offerId, ctrl.signal).then(
      (detail) => {
        if (!ctrl.signal.aborted) setLoaded({ key, status: 'success', detail });
      },
      (e: unknown) => {
        // abort로 생긴 오류는 무시한다(F10).
        if (ctrl.signal.aborted) return;
        setLoaded({ key, status: isNotFound(e) ? 'notFound' : 'error', detail: null });
      },
    );
    return () => ctrl.abort();
  }, [repo, offerId, key]);

  const retry = useCallback(() => setAttempt((n) => n + 1), []);
  const current = loaded !== null && loaded.key === key ? loaded : null;
  return {
    status: current?.status ?? 'loading',
    detail: current?.detail ?? null,
    retry,
  };
}
