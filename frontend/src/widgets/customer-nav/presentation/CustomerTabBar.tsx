import { Link, useLocation } from 'react-router';
import { useAuth } from '@/features/auth';
import { CUSTOMER_TABS, activeCustomerTab, tabTarget } from '../domain/customerTabs';

export function CustomerTabBar() {
  const active = activeCustomerTab(useLocation().pathname);
  const { state } = useAuth();
  return (
    <div className="tabs">
      {CUSTOMER_TABS.map((tab) => {
        const target = tabTarget(tab, state.status);
        const link = (
          <Link
            to={target.to}
            state={target.state}
            aria-current={tab.key === active ? 'page' : undefined}
          >
            {tab.label}
          </Link>
        );
        return tab.key === active ? <b key={tab.key}>{link}</b> : <span key={tab.key}>{link}</span>;
      })}
    </div>
  );
}
