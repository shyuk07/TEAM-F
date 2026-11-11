export function formatWon(n: number): string {
  return `${n.toLocaleString('ko-KR')}원`;
}

export function formatPoint(n: number): string {
  return `${n.toLocaleString('ko-KR')}P`;
}
