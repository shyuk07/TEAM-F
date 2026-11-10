import { Navigate, type RouteObject } from 'react-router';
import { ROUTES, ROUTE_PATTERNS } from '@/shared/lib/routes';
import { AccountLayout } from '@/app/layouts/AccountLayout';
import { CustomerLayout } from '@/app/layouts/CustomerLayout';
import { OwnerLayout } from '@/app/layouts/OwnerLayout';
import { PasswordChangePage } from '@/pages/account-password';
import { ProfilePage } from '@/pages/account-profile';
import { HomePage } from '@/pages/home';
import { LoginPage } from '@/pages/login';
import { MyPage } from '@/pages/my';
import { PasswordResetPage } from '@/pages/password-reset';
import { PointHistoryPage } from '@/pages/point-history';
import { SignupPage } from '@/pages/signup';
import { WithdrawPage } from '@/pages/withdraw';
import { TAB_BAR_HANDLE } from './handle';
import {
  OfferDetailPlaceholder,
  OwnerOfferNewPlaceholder,
  OwnerOffersPlaceholder,
  OwnerProductEditPlaceholder,
  OwnerProductNewPlaceholder,
  OwnerStorePlaceholder,
  OwnerTodayPlaceholder,
  ReservationsPlaceholder,
} from './placeholders';

export const routes: RouteObject[] = [
  {
    element: <CustomerLayout access="public" />,
    children: [
      { path: ROUTES.home, element: <HomePage />, handle: TAB_BAR_HANDLE },
      // C2: catalog 담당이 <OfferDetailPage />로 바꾼다(customer-home.md §5.3)
      { path: ROUTE_PATTERNS.offerDetail, element: <OfferDetailPlaceholder /> },
    ],
  },
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
  {
    element: <CustomerLayout access="customer" />,
    children: [
      // C5: reservations 담당이 <ReservationsPage />로 바꾼다(customer-home.md §5.3)
      {
        path: ROUTES.reservations,
        element: <ReservationsPlaceholder />,
        handle: TAB_BAR_HANDLE,
      },
      { path: ROUTES.me, element: <MyPage />, handle: TAB_BAR_HANDLE },
      { path: ROUTES.mePoints, element: <PointHistoryPage /> },
      { path: ROUTES.meWithdraw, element: <WithdrawPage /> },
      // 탭 바 없는 고객 전용 화면(결제 C3·C4, 예약 하위 화면)은 여기에 handle 없이 한 줄씩(customer-home.md §5.5)
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
  // TODO: 정의되지 않은 경로를 /로 보낸다. 전용 NotFound 화면과 문구를 정한다.
  //   왜: 문구 정본이 없다 (docs/design/frontend/app-shell.md D-16)
  //   언제: 결정 후 (사용자: NotFound 문구)
  { path: '*', element: <Navigate to={ROUTES.home} replace /> },
];
