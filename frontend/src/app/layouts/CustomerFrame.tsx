import type { ReactNode } from 'react';

// 고객 셸 프레임: PC에서도 420px 가운데(layout.md 역할별 셸, customer-home.md D-5). 토큰 변수만 쓴다(F12).
export function CustomerFrame({ children }: { children?: ReactNode }) {
  return (
    <div
      data-shell="customer"
      style={{
        maxWidth: 420,
        marginInline: 'auto',
        minHeight: '100dvh',
        display: 'flex',
        flexDirection: 'column',
        borderInline: '1px solid var(--line)',
      }}
    >
      {children}
    </div>
  );
}
