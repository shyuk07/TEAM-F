import { useState } from 'react';
import { storeStatusLabel, storeStatusTone, useOwnerStore } from '@/entities/store';
import {
  HandoverNotice,
  PickupCodeForm,
  PickupList,
  PickupTabs,
  usePickup,
  useStoreQueue,
  type PickupTab,
  type StoreReservation,
} from '@/features/reservations';
import { StoreSuspendedNotice } from '@/features/stores';
import { AppBar, StatusTag } from '@/shared/ui';
import { OwnerAccountButton, OwnerTopNav } from '@/widgets/owner-nav';

export function OwnerTodayPage() {
  const store = useOwnerStore();
  const [tab, setTab] = useState<PickupTab>('waiting');
  const [selectedReservation, setSelectedReservation] = useState<StoreReservation | null>(null);

  const storeId = store?.id ?? '';
  const { status, waiting, doneToday, counts, reload } = useStoreQueue(storeId);

  const { submit, status: pickupStatus, errorMessage, lastDone, reset } = usePickup(reload);

  if (store === null) return null;

  const currentList = tab === 'waiting' ? waiting : doneToday;

  const handleTabChange = (nextTab: PickupTab) => {
    setTab(nextTab);
    reset();
  };

  const handlePickupSubmit = async (code: string): Promise<boolean> => {
    // 임시 A안: 선택된 예약이 있으면 그 예약으로 제출, 없으면 대기 목록의 첫번째 예약 또는 에러
    const target = selectedReservation ?? (waiting.length === 1 ? waiting[0] : undefined);
    return submit(code, target);
  };

  return (
    <>
      <AppBar
        logo
        title={store.name}
        left={
          <StatusTag tone={storeStatusTone(store.status)}>
            {storeStatusLabel(store.status)}
          </StatusTag>
        }
        right={
          <>
            <OwnerTopNav />
            <OwnerAccountButton />
          </>
        }
      />

      <div className="body split r">
        <div className="grid">
          {store.status === 'SUSPENDED' && <StoreSuspendedNotice />}

          {lastDone && <HandoverNotice lastDone={lastDone} />}

          <PickupTabs
            current={tab}
            waitingCount={counts.waiting}
            doneCount={counts.done}
            onChange={handleTabChange}
          />

          <PickupList
            status={status}
            reservations={currentList}
            tab={tab}
            selectedId={selectedReservation?.id}
            onSelect={setSelectedReservation}
            onRetry={reload}
          />
        </div>

        <div
          className="box dk"
          style={{
            flexDirection: 'column',
            background: 'var(--fill)',
            alignSelf: 'start',
          }}
        >
          <PickupCodeForm
            variant="panel"
            isPending={pickupStatus === 'running'}
            errorMessage={errorMessage}
            onSubmit={handlePickupSubmit}
          />
        </div>
      </div>

      <div className="cta">
        <PickupCodeForm
          variant="cta"
          isPending={pickupStatus === 'running'}
          errorMessage={errorMessage}
          onSubmit={handlePickupSubmit}
        />
      </div>
    </>
  );
}
