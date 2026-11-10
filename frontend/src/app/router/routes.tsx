import { Navigate, type RouteObject } from 'react-router';
import { ROUTES, ROUTE_PATTERNS } from '@/shared/lib/routes';
import { OwnerLayout } from '@/app/layouts/OwnerLayout';
import {
  HomePlaceholder,
  LoginPlaceholder,
  OwnerOfferNewPlaceholder,
  OwnerOffersPlaceholder,
  OwnerProductEditPlaceholder,
  OwnerProductNewPlaceholder,
  OwnerStorePlaceholder,
  OwnerTodayPlaceholder,
} from './placeholders';

export const routes: RouteObject[] = [
  { path: ROUTES.home, element: <HomePlaceholder /> },
  { path: ROUTES.login, element: <LoginPlaceholder /> },
  { path: ROUTES.owner, element: <Navigate to={ROUTES.ownerToday} replace /> },
  {
    element: <OwnerLayout />,
    children: [
      { path: ROUTES.ownerToday, element: <OwnerTodayPlaceholder />, handle: { tabBar: true } },
      { path: ROUTES.ownerOffers, element: <OwnerOffersPlaceholder />, handle: { tabBar: true } },
      { path: ROUTES.ownerOfferNew, element: <OwnerOfferNewPlaceholder /> },
      { path: ROUTES.ownerStore, element: <OwnerStorePlaceholder />, handle: { tabBar: true } },
      { path: ROUTES.ownerProductNew, element: <OwnerProductNewPlaceholder /> },
      { path: ROUTE_PATTERNS.ownerProduct, element: <OwnerProductEditPlaceholder /> },
    ],
  },
  { path: '*', element: <Navigate to={ROUTES.home} replace /> },
];
