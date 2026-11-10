import { Outlet, useMatches } from 'react-router';
import { isTabBarHandle } from '@/app/router/handle';
import { CustomerTabBar } from '@/widgets/customer-nav';
// TODO: 420px 프레임이 이 파일의 CSS Module에만 있다.
//   왜: bundle.css에 고객 PC 프레임 클래스가 없다 (docs/design/frontend/offers.md C-6, D-5)
//   언제: 결정 후 (디자인 시스템: 고객 셸 프레임 클래스 추가)
import styles from './CustomerLayout.module.css';

// 가드 없음: C1은 공개 화면이라 로그인 여부와 무관하게 항상 그린다 (offers.md D-5)
export function CustomerLayout() {
  const showTabBar = useMatches().some((m) => isTabBarHandle(m.handle));
  return (
    <div className={styles.outer}>
      <div className={styles.frame}>
        <div className="app">
          <Outlet />
          {showTabBar ? <CustomerTabBar /> : null}
        </div>
      </div>
    </div>
  );
}
