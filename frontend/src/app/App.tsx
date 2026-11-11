import { useMemo } from 'react';
import { createBrowserRouter, RouterProvider } from 'react-router';
import { AuthFailureBridge } from '@/app/providers/AuthFailureBridge';
import { routes } from '@/app/router/routes';
import { AuthProvider } from '@/features/auth';

export function App() {
  // 마운트 시점의 window.location으로 라우터를 만든다. 모듈 임포트 시점에 만들면
  // 시작 경로가 고정되어 외부에서 URL을 바꾼 뒤 마운트하는 경우(App.test)를 반영하지 못한다.
  const router = useMemo(() => createBrowserRouter(routes), []);

  return (
    <AuthProvider>
      <AuthFailureBridge />
      <RouterProvider router={router} />
    </AuthProvider>
  );
}
