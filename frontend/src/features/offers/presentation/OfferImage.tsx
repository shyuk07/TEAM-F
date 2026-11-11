import { useState } from 'react';
import { PRODUCT_IMAGE_PLACEHOLDER } from '../domain/offerMessages';

const IMAGE_MIN_HEIGHT = 170;

// TODO: 첫 장만 표시한다. 여러 장 슬라이드는 하지 않는다.
//   왜: 여러 장 표시 방식이 정해지지 않았다 (docs/design/frontend/offers.md D-3, Q-5)
//   언제: 결정 후 (사용자: 여러 장 표시)
export function OfferImage({ urls, alt }: { urls: string[]; alt: string }) {
  const src = urls[0];
  // 실패한 주소를 기억한다. 주소가 바뀌면 다시 시도한다.
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  if (src === undefined || failedSrc === src) {
    return (
      <div className="ph" style={{ minHeight: IMAGE_MIN_HEIGHT }}>
        {PRODUCT_IMAGE_PLACEHOLDER}
      </div>
    );
  }
  return (
    <img
      src={src}
      alt={alt}
      style={{ minHeight: IMAGE_MIN_HEIGHT, width: '100%', objectFit: 'cover' }}
      onError={() => setFailedSrc(src)}
    />
  );
}
