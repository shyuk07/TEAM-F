import type { Store } from './store';

// 도메인 데이터 접근 포트. products(O4·O6·O11·O12)도 쓰므로 entities에 둔다(D-16).
export interface StoreRepository {
  /** GET /v1/stores/me. 404(상점 없음)이면 null. 그 밖의 오류는 던진다 */
  findMine(signal?: AbortSignal): Promise<Store | null>;
}
