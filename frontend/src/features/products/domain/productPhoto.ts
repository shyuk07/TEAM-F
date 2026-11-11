export const PHOTO_MAX_BYTES = 5 * 1024 * 1024;
export const PHOTO_ACCEPT = ['image/jpeg', 'image/png', 'image/webp'] as const;

export type PhotoMeta = { type: string; size: number };
export type PhotoErrorCode = 'UNSUPPORTED_TYPE' | 'TOO_LARGE' | 'EMPTY';
export type PhotoSlotPhase = 'empty' | 'filled' | 'uploading' | 'failed';

// 검사 순서: 0바이트 → 형식 → 크기
export function validatePhoto(meta: PhotoMeta): PhotoErrorCode | null {
  if (meta.size === 0) return 'EMPTY';
  if (!(PHOTO_ACCEPT as readonly string[]).includes(meta.type)) return 'UNSUPPORTED_TYPE';
  if (meta.size > PHOTO_MAX_BYTES) return 'TOO_LARGE';
  return null;
}

export function photoSlotPhase(i: {
  hasImage: boolean;
  uploading: boolean;
  error: string | null;
}): PhotoSlotPhase {
  if (i.error !== null) return 'failed';
  if (i.uploading && i.hasImage) return 'uploading'; // 사진이 없으면 칸은 empty 그대로(D-11)
  if (i.hasImage) return 'filled';
  return 'empty';
}
