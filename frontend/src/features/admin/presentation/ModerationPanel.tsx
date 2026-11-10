import { useId, useState, type FormEvent } from 'react';
import type { SanctionResult } from '../application/runSanction';
import { offerStatusView, storeStatusView, type StatusView } from '../domain/labels';
import type { SanctionKind } from '../domain/sanction';
import { isUuid } from '../domain/uuid';
import { StatusWithCode } from './AccountStatusTag';
import { SanctionSheet } from './SanctionSheet';

export type ModerationTarget = 'store' | 'offer';

type Found = { id: string; name: string | null; status: string | null };

// M5 상점 탭·할인 탭. 목록·단건 조회 API가 없어 ID를 입력해 바로 조치한다 (admin.md D-8).
// TODO: 상점·할인을 목록·단건 조회로 찾지 않고, 입력한 ID로 대상 행만 만든다(이름·상태는 조치 응답으로 채움).
//   왜: 관리자용 상점·할인 목록·단건 조회 API가 없다 (docs/design/frontend/admin.md C-1)
//   언제: 상점·할인 목록 API 추가 후
// TODO: 「ID 형식이 올바르지 않아요.」는 임시 문구다.
//   왜: screens.md M5에 ID 오류 문구가 없다 (docs/design/frontend/admin.md D-7)
//   언제: 결정 후 (디자인 시스템: content.md 관리자 오류 문구 확정)
export function ModerationPanel({ target }: { target: ModerationTarget }) {
  const inputId = useId();
  const [idText, setIdText] = useState('');
  const [inputError, setInputError] = useState<string | null>(null);
  const [found, setFound] = useState<Found | null>(null);
  const [sheet, setSheet] = useState<SanctionKind | null>(null);

  function onFind(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!isUuid(idText)) {
      setInputError('ID 형식이 올바르지 않아요.');
      setFound(null);
      return;
    }
    setInputError(null);
    setFound({ id: idText.trim(), name: null, status: null });
  }

  function onDone(result: SanctionResult) {
    setSheet(null);
    if (result.kind === 'store') {
      setFound({ id: result.store.id, name: result.store.name, status: result.store.status });
    } else if (result.kind === 'offer') {
      setFound({ id: result.offer.id, name: result.offer.title, status: result.offer.status });
    }
  }

  const statusView: StatusView | null =
    found?.status == null
      ? null
      : target === 'store'
        ? storeStatusView(found.status)
        : offerStatusView(found.status);

  return (
    <div className="body split">
      <form className="box" onSubmit={onFind} noValidate>
        <div className="warn">
          상점·할인 목록 API가 아직 없어요(<b>확인 필요</b>). 지금은 ID로만 찾을 수 있어요.
        </div>
        <label className="lbl" htmlFor={inputId}>
          상점 ID 또는 할인 ID
        </label>
        <input
          id={inputId}
          className="in"
          style={{ fontFamily: 'var(--mono)', color: 'var(--fg)' }}
          value={idText}
          autoComplete="off"
          spellCheck={false}
          onChange={(e) => setIdText(e.target.value)}
        />
        {inputError !== null ? (
          <div className="err" role="alert">
            {inputError}
          </div>
        ) : null}
        <button type="submit" className="btn">
          찾기
        </button>
      </form>
      <div className="list">
        {target === 'store' ? (
          <div className="tr th">
            <span className="lbl">상점</span>
            <span className="lbl">주소</span>
            <span className="lbl">개설일</span>
            <span className="lbl">상태</span>
            <span></span>
          </div>
        ) : (
          <div className="tr th">
            <span className="lbl">상품명</span>
            <span className="lbl">상점</span>
            <span></span>
            <span className="lbl">판매 상태</span>
            <span></span>
          </div>
        )}
        {found !== null ? (
          <div className="tr">
            <div style={{ minWidth: 0 }}>
              {found.name !== null ? <b>{found.name}</b> : null}
              <div className="code-tag" style={{ overflowWrap: 'anywhere' }}>
                {found.id}
              </div>
            </div>
            <span className="hide">–</span>
            <span className="hide">–</span>
            {statusView !== null && found.status !== null ? (
              <StatusWithCode view={statusView} code={found.status} className="hide" />
            ) : (
              <span className="hide">–</span>
            )}
            <span className="row">
              {target === 'store' ? (
                <>
                  <button type="button" className="btn sm" onClick={() => setSheet('suspendStore')}>
                    정지
                  </button>
                  <button
                    type="button"
                    className="link"
                    style={{ background: 'none', border: 0, padding: 0, cursor: 'pointer' }}
                    onClick={() => setSheet('closeStore')}
                  >
                    강제 폐점
                  </button>
                </>
              ) : (
                <button type="button" className="btn sm" onClick={() => setSheet('suspendOffer')}>
                  할인 정지
                </button>
              )}
            </span>
          </div>
        ) : null}
      </div>
      {sheet !== null && found !== null ? (
        <SanctionSheet
          kind={sheet}
          target={{ id: found.id, label: found.name ?? found.id }}
          onClose={() => setSheet(null)}
          onDone={onDone}
        />
      ) : null}
    </div>
  );
}
