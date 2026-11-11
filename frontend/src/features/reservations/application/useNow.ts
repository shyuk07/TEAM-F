import { useEffect, useState } from 'react';

// TODO: 현재 시각을 30초마다 갱신한다. 주기는 임시값이다.
//   왜: 화면 시각 갱신 주기 정본이 없다 (docs/design/frontend/reservations.md D-9)
//   언제: 결정 후 (사용자: 시각 갱신 주기)
export function useNow(intervalMs = 30000): Date {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}
