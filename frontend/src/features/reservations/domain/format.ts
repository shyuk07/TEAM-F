// 표시 시간대는 브라우저와 무관하게 KST로 고정한다(오케스트레이터 확정).
const TIME_ZONE = 'Asia/Seoul';

const partsFormat = new Intl.DateTimeFormat('en-US', {
  timeZone: TIME_ZONE,
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
  hour: '2-digit',
  minute: '2-digit',
  hourCycle: 'h23',
});

function kstParts(d: Date): Record<'year' | 'month' | 'day' | 'hour' | 'minute', string> {
  const out = { year: '', month: '', day: '', hour: '', minute: '' };
  for (const p of partsFormat.formatToParts(d)) {
    if (p.type in out) out[p.type as keyof typeof out] = p.value;
  }
  return out;
}

export function formatWon(n: number): string {
  return `${n.toLocaleString('ko-KR')}원`;
}

export function formatTime(d: Date): string {
  const p = kstParts(d);
  return `${p.hour}:${p.minute}`;
}

export function formatTimeRange(a: Date, b: Date): string {
  return `${formatTime(a)}\u2013${formatTime(b)}`;
}

export function formatDate(d: Date): string {
  const p = kstParts(d);
  return `${p.month}/${p.day}`;
}

export function isSameKstDate(a: Date, b: Date): boolean {
  const x = kstParts(a);
  const y = kstParts(b);
  return x.year === y.year && x.month === y.month && x.day === y.day;
}

export function formatQuantity(name: string, q: number): string {
  return `${name} × ${q}`;
}
