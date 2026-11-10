// 업무를 모르는 숫자·날짜 표기(customer-home.md §2.1, D-26). 시각은 브라우저 로컬 기준(D-13).

function pad2(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}

// 정수 천 단위 쉼표. 음수는 `-` 접두. Intl 없이 계산한다.
export function groupDigits(n: number): string {
  const negative = n < 0;
  const digits = String(Math.trunc(Math.abs(n)));
  let out = '';
  for (let i = 0; i < digits.length; i++) {
    if (i > 0 && (digits.length - i) % 3 === 0) out += ',';
    out += digits[i];
  }
  return negative ? `-${out}` : out;
}

export function formatHm(d: Date): string {
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

export function formatMd(d: Date): string {
  return `${pad2(d.getMonth() + 1)}/${pad2(d.getDate())}`;
}

export function isSameLocalDate(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}
