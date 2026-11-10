import { AdminNavItems } from './AdminNavItems';

export function AdminTabBar() {
  return (
    <nav className="tabs" aria-label="관리자 메뉴">
      <AdminNavItems />
    </nav>
  );
}
