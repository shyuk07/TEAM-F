import { Navigate, type RouteObject } from 'react-router';
import { ROUTES, ROUTE_PATTERNS } from '@/shared/lib/routes';
import { OwnerLayout } from '@/app/layouts/OwnerLayout';
import { LoginPage } from '@/pages/login';
import { TAB_BAR_HANDLE } from './handle';
import {
  HomePlaceholder,
  OwnerOfferNewPlaceholder,
  OwnerOffersPlaceholder,
  OwnerProductEditPlaceholder,
  OwnerProductNewPlaceholder,
  OwnerStorePlaceholder,
  OwnerTodayPlaceholder,
} from './placeholders';

export const routes: RouteObject[] = [
  { path: ROUTES.home, element: <HomePlaceholder /> },
  { path: ROUTES.login, element: <LoginPage /> },
  { path: ROUTES.owner, element: <Navigate to={ROUTES.ownerToday} replace /> },
  {
    element: <OwnerLayout />,
    children: [
      { path: ROUTES.ownerToday, element: <OwnerTodayPlaceholder />, handle: TAB_BAR_HANDLE },
      { path: ROUTES.ownerOffers, element: <OwnerOffersPlaceholder />, handle: TAB_BAR_HANDLE },
      { path: ROUTES.ownerOfferNew, element: <OwnerOfferNewPlaceholder /> },
      { path: ROUTES.ownerStore, element: <OwnerStorePlaceholder />, handle: TAB_BAR_HANDLE },
      { path: ROUTES.ownerProductNew, element: <OwnerProductNewPlaceholder /> },
      { path: ROUTE_PATTERNS.ownerProduct, element: <OwnerProductEditPlaceholder /> },
    ],
  },
  // TODO: 정의되지 않은 경로를 /로 보낸다. 전용 NotFound 화면과 문구를 정한다.
  //   왜: 문구 정본이 없다 (docs/design/frontend/app-shell.md D-16)
  //   언제: 결정 후 (사용자: NotFound 문구)
  { path: '*', element: <Navigate to={ROUTES.home} replace /> },
];
