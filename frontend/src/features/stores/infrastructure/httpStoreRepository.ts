import { apiGet } from '@/shared/api/client';
import { ApiError } from '@/shared/api/error';
import type { Store, StoreRepository } from '@/entities/store';
import { toStore, type MyStoreDto } from './storeDto';

// store entity 포트의 구현체. store 개체의 소유 영역은 stores(F18, fsd-structure §1.1).
export class HttpStoreRepository implements StoreRepository {
  // 404 && NOT_FOUND(상점 없음)이면 null, 그 밖의 오류는 그대로 던진다.
  async findMine(signal?: AbortSignal): Promise<Store | null> {
    try {
      const dto: MyStoreDto = await apiGet<MyStoreDto>('/v1/stores/me', signal);
      return toStore(dto);
    } catch (e) {
      if (e instanceof ApiError && e.status === 404 && e.errorCode === 'NOT_FOUND') return null;
      throw e;
    }
  }
}
