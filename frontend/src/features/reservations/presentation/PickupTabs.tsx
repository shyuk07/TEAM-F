import { Chip } from '@/shared/ui/Chip';

export type PickupTab = 'waiting' | 'done';

export type PickupTabsProps = {
  current: PickupTab;
  waitingCount: number;
  doneCount: number;
  onChange: (tab: PickupTab) => void;
};

export function PickupTabs({ current, waitingCount, doneCount, onChange }: PickupTabsProps) {
  return (
    <div className="scroll" role="toolbar" aria-label="픽업 큐 탭">
      <Chip selected={current === 'waiting'} onClick={() => onChange('waiting')}>
        픽업 대기 {waitingCount}
      </Chip>
      <Chip selected={current === 'done'} onClick={() => onChange('done')}>
        완료 {doneCount}
      </Chip>
    </div>
  );
}
