import { WIDEN_RADIUS_KM } from './search';

export type EmptyAction = 'clearKeyword' | 'widenRadius' | null;

export type EmptyView = {
  title: string;
  reason: string;
  action: EmptyAction;
  actionLabel: string | null;
};

// TODO: 임시 문구다(빈 목록(검색어 있음), 오류, 「더 보기」, 더 보기 실패, 위치 칩 라벨).
//   왜: screens.md·content.md에 C1 목록 상태 문구가 없다 (docs/design/frontend/offers.md D-20, D-21, D-23, D-32)
//   언제: 결정 후 (디자인 시스템: content.md C1 문구 확정)
export function emptyView(input: {
  keyword: string | undefined;
  hasLocation: boolean;
  radiusKm: number;
}): EmptyView {
  if (input.keyword !== undefined) {
    return {
      title: '검색 결과가 없어요',
      reason: '다른 상품명으로 검색해 보세요.',
      action: 'clearKeyword',
      actionLabel: '검색어 지우기',
    };
  }
  const title = '근처에 마감 할인이 없어요';
  const reason = '반경을 넓히거나 저녁 시간에 다시 확인해 보세요.';
  if (input.hasLocation && input.radiusKm < WIDEN_RADIUS_KM) {
    return {
      title,
      reason,
      action: 'widenRadius',
      actionLabel: `반경 ${WIDEN_RADIUS_KM}km로 넓히기`,
    };
  }
  return { title, reason, action: null, actionLabel: null };
}
