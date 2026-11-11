import { useState, type FormEvent } from 'react';
import type { Store } from '@/entities/store';
import { Button, CtaBar, Input, Notice } from '@/shared/ui';
import { canSubmitClose } from '../domain/closeStoreInput';
import { useCloseStore } from '../application/useCloseStore';

// TODO: 폐점을 막는 항목(진행 중·예정 할인, 픽업 대기 예약)을 먼저 보여 주지 않고, 막는 항목이 0일 때만 버튼을 활성화하지도 않는다. 상점명이 맞으면 눌리고 서버 400 문구만 보인다.
//   왜: 막는 항목을 셀 offers·reservations 영역이 아직 없다 (docs/design/frontend/stores.md D-3, screens.md O7)
//   언제: offers 구현 시, reservations 구현 시
export function StoreCloseForm(props: { store: Store; onCancel(): void }) {
  const { store, onCancel } = props;
  const [typedName, setTypedName] = useState('');
  const { submit, pending, errorMessage } = useCloseStore(store);

  // 상점명 완전 일치(NFC, D-8)와 pending 중 비활성(F10).
  const disabled = !canSubmitClose(typedName, store.name) || pending;

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (disabled) return;
    void submit(typedName).catch(() => undefined);
  }

  // .body와 CtaBar 두 형제. 취소는 pending 중에도 눌린다. 두 벌의 버튼은 같은 폼을 제출한다(D-18).
  return (
    <>
      <div className="body">
        <Notice>폐점하면 다시 열 수 없고, 이 계정으로 새 상점도 만들 수 없어요.</Notice>
        <form id="store-close-form" noValidate onSubmit={onSubmit}>
          <Input
            label={
              <>
                확인을 위해 상점명을 입력하세요: <b>{store.name}</b>
              </>
            }
            value={typedName}
            onChange={setTypedName}
            error={errorMessage}
          />
          <Button type="button" desktopOnly onClick={onCancel}>
            취소
          </Button>
          <Button variant="dark" desktopOnly type="submit" disabled={disabled} pending={pending}>
            폐점하기
          </Button>
        </form>
      </div>
      <CtaBar>
        <Button type="button" onClick={onCancel}>
          취소
        </Button>
        <Button
          variant="dark"
          type="submit"
          form="store-close-form"
          disabled={disabled}
          pending={pending}
        >
          폐점하기
        </Button>
      </CtaBar>
    </>
  );
}
