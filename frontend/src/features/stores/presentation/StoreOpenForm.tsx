import { useState, type FormEvent } from 'react';
import { Box, Button, CtaBar, Input } from '@/shared/ui';
import { canSubmitOpenStore } from '../domain/openStoreInput';
import { useOpenStore } from '../application/useOpenStore';

// open-issues: C8 상점은 가입 시 상호를 이름으로 복사해 만든다. 이름은 입력받지 않는다.
export function StoreOpenForm(props: { ownerName: string }) {
  const { ownerName } = props;
  const [address, setAddress] = useState('');
  const { submit, pending, errorMessage } = useOpenStore();

  // 계정 name이 null로 오면(빈 값) 폼 대신 개설 불가 안내를 그린다(D-21 임시).
  if (ownerName === '') {
    return (
      <div className="body">
        <Box title="상점 개설">
          <div className="m">계정 정보가 올바르지 않아 상점을 열 수 없어요.</div>
        </Box>
      </div>
    );
  }

  const disabled = !canSubmitOpenStore(address) || pending;

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (disabled) return;
    void submit(address).catch(() => undefined);
  }

  // .body와 CtaBar 두 형제(.app 직속 레이아웃). 두 「상점 열기」 버튼은 같은 폼을 제출한다(D-18).
  return (
    <>
      <div className="body">
        <Box title="상점 개설">
          <form id="store-open-form" noValidate onSubmit={onSubmit}>
            {/* 상점명 칸은 읽기 전용. 개설 요청은 pickup_address만 보낸다(D-20). */}
            <Input
              label="상점명 (가입 시 상호)"
              value={ownerName}
              onChange={() => undefined}
              readOnly
            />
            <Input
              label="픽업 주소"
              value={address}
              onChange={setAddress}
              required
              maxLength={500}
              autoComplete="street-address"
              error={errorMessage}
            />
            <Button variant="primary" desktopOnly type="submit" disabled={disabled} pending={pending}>
              상점 열기
            </Button>
          </form>
        </Box>
      </div>
      <CtaBar>
        <Button variant="primary" type="submit" form="store-open-form" disabled={disabled} pending={pending}>
          상점 열기
        </Button>
      </CtaBar>
    </>
  );
}
