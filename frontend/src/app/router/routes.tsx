import { Navigate, type RouteObject } from 'react-router';
import { ROUTES, ROUTE_PATTERNS } from '@/shared/lib/routes';
import { AccountLayout } from '@/app/layouts/AccountLayout';
import { AdminLayout } from '@/app/layouts/AdminLayout';
import { OwnerLayout } from '@/app/layouts/OwnerLayout';
import { PasswordChangePage } from '@/pages/account-password';
import { ProfilePage } from '@/pages/account-profile';
import { AdminApprovalsPage } from '@/pages/admin-approvals';
import { AdminOffersPage, AdminStoresPage } from '@/pages/admin-moderation';
import { AdminUsersPage } from '@/pages/admin-users';
import { LoginPage } from '@/pages/login';
import { PasswordResetPage } from '@/pages/password-reset';
import { SignupPage } from '@/pages/signup';
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
  { path: ROUTES.signup, element: <SignupPage /> },
  { path: ROUTES.passwordReset, element: <PasswordResetPage /> },
  { path: ROUTES.account, element: <Navigate to={ROUTES.accountProfile} replace /> },
  {
    element: <AccountLayout />,
    children: [
      { path: ROUTES.accountProfile, element: <ProfilePage /> },
      { path: ROUTES.accountPassword, element: <PasswordChangePage /> },
    ],
  },
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
  { path: ROUTES.admin, element: <Navigate to={ROUTES.adminApprovals} replace /> },
  {
    element: <AdminLayout />,
    children: [
      { path: ROUTES.adminApprovals, element: <AdminApprovalsPage />, handle: TAB_BAR_HANDLE },
      { path: ROUTES.adminUsers, element: <AdminUsersPage />, handle: TAB_BAR_HANDLE },
      { path: ROUTE_PATTERNS.adminUser, element: <AdminUsersPage /> },
      { path: ROUTES.adminStores, element: <AdminStoresPage />, handle: TAB_BAR_HANDLE },
      { path: ROUTES.adminOffers, element: <AdminOffersPage />, handle: TAB_BAR_HANDLE },
    ],
  },
  // TODO: 정의되지 않은 경로를 /로 보낸다. 전용 NotFound 화면과 문구를 정한다.
  //   왜: 문구 정본이 없다 (docs/design/frontend/app-shell.md D-16)
  //   언제: 결정 후 (사용자: NotFound 문구)
  { path: '*', element: <Navigate to={ROUTES.home} replace /> },
];
