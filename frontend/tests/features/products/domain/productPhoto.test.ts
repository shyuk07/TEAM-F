import { describe, expect, it } from 'vitest';
import { photoSlotPhase, validatePhoto } from '@/features/products/domain/productPhoto';

describe('features/products domain productPhoto', () => {
  describe('validatePhoto', () => {
    it.each(['image/jpeg', 'image/png', 'image/webp'])('%s 1바이트는 null(통과)', (type) => {
      expect(validatePhoto({ type, size: 1 })).toBeNull();
    });

    it.each(['image/gif', 'application/pdf'])('%s → UNSUPPORTED_TYPE', (type) => {
      expect(validatePhoto({ type, size: 1000 })).toBe('UNSUPPORTED_TYPE');
    });

    it('0바이트는 형식이 맞아도 EMPTY', () => {
      expect(validatePhoto({ type: 'image/jpeg', size: 0 })).toBe('EMPTY');
    });

    it('정확히 5MiB(5,242,880)는 통과, 5,242,881은 TOO_LARGE', () => {
      expect(validatePhoto({ type: 'image/png', size: 5_242_880 })).toBeNull();
      expect(validatePhoto({ type: 'image/png', size: 5_242_881 })).toBe('TOO_LARGE');
    });

    it('형식 오류와 크기 초과가 겹치면 UNSUPPORTED_TYPE', () => {
      expect(validatePhoto({ type: 'image/gif', size: 6_000_000 })).toBe('UNSUPPORTED_TYPE');
    });
  });

  describe('photoSlotPhase', () => {
    const base = { hasImage: false, uploading: false, error: null };

    it('아무것도 없으면 empty', () => {
      expect(photoSlotPhase(base)).toBe('empty');
    });

    it('hasImage → filled', () => {
      expect(photoSlotPhase({ ...base, hasImage: true })).toBe('filled');
    });

    // B2: 사진이 없으면 uploading이어도 empty
    it('사진 없이 uploading이면 empty', () => {
      expect(photoSlotPhase({ ...base, uploading: true })).toBe('empty');
    });

    it('error 문자열이 있으면 다른 값보다 우선해 failed', () => {
      expect(photoSlotPhase({ hasImage: true, uploading: true, error: '실패' })).toBe('failed');
    });

    it('uploading과 hasImage가 둘 다면 uploading', () => {
      expect(photoSlotPhase({ ...base, hasImage: true, uploading: true })).toBe('uploading');
    });
  });
});
