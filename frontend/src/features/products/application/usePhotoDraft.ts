import { useCallback, useEffect, useRef, useState } from 'react';
import { photoErrorMessage } from '../domain/productMessages';
import { validatePhoto } from '../domain/productPhoto';

export function usePhotoDraft(): {
  file: Blob | null;
  previewSrc: string | null;
  error: string | null;
  pick(file: File): void;
  clear(): void;
} {
  const [file, setFile] = useState<Blob | null>(null);
  const [previewSrc, setPreviewSrc] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const urlRef = useRef<string | null>(null);

  const revoke = useCallback(() => {
    if (urlRef.current !== null) {
      URL.revokeObjectURL(urlRef.current);
      urlRef.current = null;
    }
  }, []);

  useEffect(() => revoke, [revoke]);

  const pick = useCallback(
    (next: File) => {
      const code = validatePhoto({ type: next.type, size: next.size });
      if (code !== null) {
        // 검증 실패: 이전 사진·미리보기를 버리고 오류만 남긴다(A2, D-34)
        revoke();
        setFile(null);
        setPreviewSrc(null);
        setError(photoErrorMessage(code));
        return;
      }
      revoke();
      const url = URL.createObjectURL(next);
      urlRef.current = url;
      setFile(next);
      setPreviewSrc(url);
      setError(null);
    },
    [revoke],
  );

  const clear = useCallback(() => {
    revoke();
    setFile(null);
    setPreviewSrc(null);
    setError(null);
  }, [revoke]);

  return { file, previewSrc, error, pick, clear };
}
