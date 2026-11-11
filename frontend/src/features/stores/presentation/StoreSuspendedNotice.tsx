import { Box, StatusTag } from '@/shared/ui';

// O1 정지 안내 부품(D-22): 정지 상점주는 현재 계정 정지로 로그인 불가라 도달하지 않지만,
// 백엔드 확인(C-1) 전까지 부품을 유지한다. 배치 검토는 O1 구현 때(N-5).
export function StoreSuspendedNotice() {
  return (
    <Box
      tag={<StatusTag tone="hot">상점 정지</StatusTag>}
      title="관리자가 상점을 정지했어요"
    >
      <div className="m">새 할인을 올릴 수 없어요. 기존 예약의 픽업은 처리할 수 있어요.</div>
    </Box>
  );
}
