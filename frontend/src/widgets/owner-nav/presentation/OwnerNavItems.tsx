import { Link, useLocation } from 'react-router';
import { OWNER_TABS, activeOwnerTab } from '../domain/ownerTabs';

export function OwnerNavItems() {
  const active = activeOwnerTab(useLocation().pathname);
  return (
    <>
      {OWNER_TABS.map((tab) => {
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
