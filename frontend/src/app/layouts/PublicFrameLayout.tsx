import { Outlet } from 'react-router';
import { CustomerFrame } from './CustomerFrame';

// 공개(로그인 전) 화면 프레임 A1~A3: PC에서 420px 가운데(app-shell.md §12). 가드·TabBar 없음.
export function PublicFrameLayout() {
  return (
    <CustomerFrame>
      <Outlet />
    </CustomerFrame>
  );
}
