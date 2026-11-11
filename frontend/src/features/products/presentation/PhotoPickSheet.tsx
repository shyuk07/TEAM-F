import { useId, useRef, type ChangeEvent } from 'react';
import { Overlay } from '@/shared/ui/Overlay';
import { PHOTO_ACCEPT } from '../domain/productPhoto';
import { PRODUCT_TEXT } from '../domain/productMessages';

// O12 ① 사진 고르기 시트. 파일을 고르면 onPick 뒤 onClose.
export function PhotoPickSheet({ onPick, onClose }: { onPick(file: File): void; onClose(): void }) {
  const titleId = useId();
  const cameraRef = useRef<HTMLInputElement>(null);
  const albumRef = useRef<HTMLInputElement>(null);

  function onChange(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file === undefined) return;
    onPick(file);
    onClose();
  }

  return (
    <Overlay onClose={onClose}>
      <div className="sheet" role="dialog" aria-modal="true" aria-labelledby={titleId}>
        <div className="t" id={titleId}>
          {PRODUCT_TEXT.photo.sheetTitle}
        </div>
        <button type="button" className="btn" onClick={() => cameraRef.current?.click()}>
          {PRODUCT_TEXT.photo.camera}
        </button>
        <button type="button" className="btn" onClick={() => albumRef.current?.click()}>
          {PRODUCT_TEXT.photo.album}
        </button>
        <div className="m">{PRODUCT_TEXT.photo.sheetHint}</div>
        <button
          type="button"
          className="link"
          style={{ background: 'none', border: 0, padding: 0, cursor: 'pointer' }}
          onClick={onClose}
        >
          {PRODUCT_TEXT.photo.cancel}
        </button>
        <input
          ref={cameraRef}
          type="file"
          accept="image/*"
          capture="environment"
          hidden
          onChange={onChange}
        />
        <input
          ref={albumRef}
          type="file"
          accept={PHOTO_ACCEPT.join(',')}
          hidden
          onChange={onChange}
        />
      </div>
    </Overlay>
  );
}
