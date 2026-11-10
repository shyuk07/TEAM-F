import type { ReactNode } from 'react';
import { Box, StatusTag } from '@/shared/ui';

type View = 'pending' | 'rejected' | 'closed' | 'account-blocked';

// open-issues: O0 거절된 상점주의 다시 신청 기능은 아직 없다.
const VIEW_CONTENT: Record<View, { tone: 'hot' | 'mute'; tag: string; title?: string; desc?: ReactNode }> = {
  pending: {
    tone: 'hot',
    tag: '승인 대기',
    title: '승인 대기 중이에요',
    desc: '관리자가 확인하면 상점을 열 수 있어요.',
  },
  rejected: {
    tone: 'mute',
    tag: '거절됨',
    title: '가입이 거절되었습니다',
    desc: '다시 신청하는 기능은 아직 없어요.',
  },
  closed: {
    tone: 'mute',
    tag: '폐점',
    title: '폐점한 상점이에요',
    desc: '이 계정으로 새 상점을 열 수 없어요.',
  },
  // 정지 상점주는 계정도 정지되어 도달하지 못하는 방어용 분기다(N-3, D-22). 문구는 없다.
  'account-blocked': { tone: 'hot', tag: '정지' },
};

// .body만 돌려준다. 한 번에 한 박스만 그린다.
export function StoreStartNotice(props: { view: View }) {
  const content = VIEW_CONTENT[props.view];
  return (
    <div className="body">
      <Box tag={<StatusTag tone={content.tone}>{content.tag}</StatusTag>} title={content.title}>
        {content.desc !== undefined ? <div className="m">{content.desc}</div> : null}
      </Box>
    </div>
  );
}
