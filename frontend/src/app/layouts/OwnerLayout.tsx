import { Outlet, useMatches } from 'react-router';
import { isTabBarHandle } from '@/app/router/handle';
import { OwnerTabBar } from '@/widgets/owner-nav';

export function OwnerLayout() {
  const showTabBar = useMatches().some((m) => isTabBarHandle(m.handle));
  // FIXME: 인증 가드가 항상 통과한다. 로그인하지 않아도 상점주 화면이 열린다.
  //   왜: auth 영역 구현 전이라 세션을 확인할 수단이 없다 (docs/design/frontend/app-shell.md D-9)
  //   언제: auth 구현 시, 늦어도 배포 전
  return (
    <div className="app">
      <Outlet />
      {showTabBar ? <OwnerTabBar /> : null}
    </div>
  );
}
