import { Link, useLocation } from 'react-router';
import { CUSTOMER_TABS, activeCustomerTab } from '../domain/customerTabs';

// 탭은 로그인 여부를 따지지 않는 일반 링크다. 비로그인이면 고객 가드가 A1로 보낸다(customer-home.md D-6).
// TODO: 탭 바 nav 접근 이름 「고객 메뉴」는 임시 문구다. 정본 문구가 정해지면 바꾼다.
//   왜: screens.md·content.md에 탭 바 접근 이름이 없다 (docs/design/frontend/customer-home.md D-6)
//   언제: 결정 후 (디자인 시스템: content.md 문구 확정)
export function CustomerTabBar() {
  const active = activeCustomerTab(useLocation().pathname);
  return (
    <nav className="tabs" aria-label="고객 메뉴">
      {CUSTOMER_TABS.map((tab) => {
        const link = (
          <Link to={tab.path} aria-current={tab.key === active ? 'page' : undefined}>
            {tab.label}
          </Link>
        );
        return tab.key === active ? <b key={tab.key}>{link}</b> : <span key={tab.key}>{link}</span>;
      })}
    </nav>
  );
}
