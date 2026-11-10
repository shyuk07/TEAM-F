import type { PageSummary } from '../domain/userQuery';

// 「1–20 / 134명」 「이전」 「다음」 (screens.md M3)
export function Pager({
  summary,
  onPrev,
  onNext,
}: {
  summary: PageSummary;
  onPrev(): void;
  onNext(): void;
}) {
  return (
    <div className="row">
      <span className="m">{summary.text}</span>
      <span className="sp"></span>
      <button type="button" className="btn sm" disabled={!summary.hasPrev} onClick={onPrev}>
        이전
      </button>
      <button type="button" className="btn sm" disabled={!summary.hasNext} onClick={onNext}>
        다음
      </button>
    </div>
  );
}
