import { readErrorInfo } from '../application/errorInfo';
import { actionErrorMessage } from '../domain/actionError';

export function ListSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="list" aria-busy="true" aria-label="불러오는 중">
      {Array.from({ length: rows }, (_, i) => (
        <div className="tr" key={i}>
          <div style={{ display: 'grid', gap: 'var(--s2)' }}>
            <div className="sk" style={{ width: '50%' }} />
            <div className="sk" style={{ width: '80%' }} />
          </div>
        </div>
      ))}
    </div>
  );
}

// TODO: 「다시 시도」는 임시 문구다(auth.md D-9와 같은 문구).
//   왜: 목록 불러오기 실패 문구 정본이 없다 (docs/design/frontend/admin.md D-7)
//   언제: 결정 후 (디자인 시스템: content.md 관리자 오류 문구 확정)
export function LoadError({ error, onRetry }: { error: unknown; onRetry(): void }) {
  return (
    <div style={{ display: 'grid', gap: 'var(--s2)' }}>
      <div className="warn" role="alert">
        {actionErrorMessage(readErrorInfo(error))}
      </div>
      <button type="button" className="btn sm" style={{ justifySelf: 'start' }} onClick={onRetry}>
        다시 시도
      </button>
    </div>
  );
}
