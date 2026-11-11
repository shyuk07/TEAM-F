import { vi } from 'vitest';
import type { MapRenderer } from '@/features/offers';

// 기본: 그리기 성공(resolve)
export class FakeMapRenderer implements MapRenderer {
  render = vi.fn<MapRenderer['render']>(() => Promise.resolve());
}
