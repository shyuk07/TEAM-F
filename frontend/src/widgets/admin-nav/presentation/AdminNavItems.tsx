import { Link, useLocation } from 'react-router';
import { ADMIN_TABS, activeAdminTab } from '../domain/adminTabs';

export function AdminNavItems() {
  const active = activeAdminTab(useLocation().pathname);
  return (
    <>
      {ADMIN_TABS.map((tab) => {
        const link = (
          <Link to={tab.path} aria-current={tab.key === active ? 'page' : undefined}>
            {tab.label}
          </Link>
        );
        return tab.key === active ? <b key={tab.key}>{link}</b> : <span key={tab.key}>{link}</span>;
      })}
    </>
  );
}
