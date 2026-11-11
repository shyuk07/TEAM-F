import { useState } from 'react';
import { Button, FieldError } from '@/shared/ui';
import { PRODUCT_TEXT } from '../domain/productMessages';
import type { PhotoSlotPhase } from '../domain/productPhoto';
import { PhotoPickSheet } from './PhotoPickSheet';

const linkButton = { background: 'none', border: 0, padding: 0, cursor: 'pointer' } as const;

export function PhotoField(props: {
  phase: PhotoSlotPhase;
  src: string | null;
  errorMessage: string | null;
  hasImage: boolean;
  onPick(file: File): void;
  onRemove?(): void;
  onRetry?(): void;
  disabled?: boolean;
}) {
  const { phase, src, errorMessage, hasImage, onPick, onRemove, onRetry, disabled } = props;
  const [sheetOpen, setSheetOpen] = useState(false);
  const blocked = disabled === true;
  const openSheet = () => {
    if (!blocked) setSheetOpen(true);
  };
  const showImage = hasImage && src !== null && src !== '';

  const image = showImage ? (
    <img
      src={src}
      alt=""
      style={{
        position: 'absolute',
        inset: 0,
        width: '100%',
        height: '100%',
        objectFit: 'cover',
        borderRadius: 'var(--r)',
      }}
    />
  ) : null;

  return (
    <div style={{ display: 'grid', gap: 'var(--s2)' }}>
      {phase === 'empty' ? (
        <button
          type="button"
          className="ph photo"
          aria-disabled={blocked ? 'true' : undefined}
          onClick={openSheet}
        >
          <span style={{ display: 'grid', justifyItems: 'center', gap: 4 }}>
            <b style={{ fontSize: 22 }}>+</b>
            <span>{PRODUCT_TEXT.photo.empty}</span>
          </span>
        </button>
      ) : (
        <div
          className="ph photo"
          style={phase === 'failed' ? { borderColor: 'var(--accent)' } : undefined}
        >
          {image}
        </div>
      )}

      {phase === 'filled' ? (
        <div className="row">
          <Button size="sm" disabled={blocked} onClick={openSheet}>
            {PRODUCT_TEXT.photo.change}
          </Button>
          <span className="sp" />
          {onRemove !== undefined ? (
            <button
              type="button"
              className="link"
              style={linkButton}
              aria-disabled={blocked ? 'true' : undefined}
              onClick={() => {
                if (!blocked) onRemove();
              }}
            >
              {PRODUCT_TEXT.photo.remove}
            </button>
          ) : null}
        </div>
      ) : null}

      {phase === 'uploading' ? (
        <div className="row">
          <span className="m">{PRODUCT_TEXT.photo.uploading}</span>
        </div>
      ) : null}

      {phase === 'failed' ? (
        <>
          {errorMessage !== null ? <FieldError>{errorMessage}</FieldError> : null}
          <div className="row">
            {onRetry !== undefined ? (
              <button
                type="button"
                className="link"
                style={linkButton}
                aria-disabled={blocked ? 'true' : undefined}
                onClick={() => {
                  if (!blocked) onRetry();
                }}
              >
                {PRODUCT_TEXT.photo.retry}
              </button>
            ) : null}
            <span className="sp" />
            <Button size="sm" disabled={blocked} onClick={openSheet}>
              {PRODUCT_TEXT.photo.pickOther}
            </Button>
          </div>
        </>
      ) : null}

      {sheetOpen ? <PhotoPickSheet onPick={onPick} onClose={() => setSheetOpen(false)} /> : null}
    </div>
  );
}
