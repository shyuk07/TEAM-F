import { useCallback, useEffect, useRef, useState } from 'react';
import { useDep } from '@/shared/lib/di';
import { actionErrorMessage } from '../domain/actionError';
import type { AdminRepository } from '../domain/adminRepository';
import { readErrorInfo } from './errorInfo';
import { AdminRepositoryToken } from './tokens';

export type MutationOutcome<T> = { ok: true; value: T } | { ok: false };

// 데이터를 바꾸는 요청: 중복 제출을 막고 pending·오류 문구를 돌려준다 (react-implementation §4).
export function useAdminMutation() {
  const admin = useDep(AdminRepositoryToken);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const running = useRef(false);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const run = useCallback(
    async <T>(task: (admin: AdminRepository) => Promise<T>): Promise<MutationOutcome<T>> => {
      if (running.current) return { ok: false };
      running.current = true;
      setPending(true);
      setError(null);
      try {
        const value = await task(admin);
        return { ok: true, value };
      } catch (e) {
        if (mounted.current) setError(actionErrorMessage(readErrorInfo(e)));
        return { ok: false };
      } finally {
        running.current = false;
        if (mounted.current) setPending(false);
      }
    },
    [admin],
  );

  const clearError = useCallback(() => setError(null), []);

  return { run, pending, error, clearError };
}
