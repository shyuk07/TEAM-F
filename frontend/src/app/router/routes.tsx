import { Navigate, type RouteObject } from 'react-router';
import { ROUTES, ROUTE_PATTERNS } from '@/shared/lib/routes';
import { AccountLayout } from '@/app/layouts/AccountLayout';
import { AdminLayout } from '@/app/layouts/AdminLayout';
import { CustomerLayout } from '@/app/layouts/CustomerLayout';
import { OwnerLayout } from '@/app/layouts/OwnerLayout';
import { PublicFrameLayout } from '@/app/layouts/PublicFrameLayout';
import { PasswordChangePage } from '@/pages/account-password';
import { ProfilePage } from '@/pages/account-profile';
import { AdminApprovalsPage } from '@/pages/admin-approvals';
import { AdminOffersPage, AdminStoresPage } from '@/pages/admin-moderation';
import { AdminUsersPage } from '@/pages/admin-users';
import { HomePage } from '@/pages/home';
import { LoginPage } from '@/pages/login';
import { MyPage } from '@/pages/my';
import { PasswordResetPage } from '@/pages/password-reset';
import { PointHistoryPage } from '@/pages/point-history';
import { SignupPage } from '@/pages/signup';
import { WithdrawPage } from '@/pages/withdraw';
import { OwnerStartPage } from '@/pages/owner-start';
import { OwnerStorePage } from '@/pages/owner-store';
import { ProductEditPage } from '@/pages/product-edit';
import { ProductNewPage } from '@/pages/product-new';
import { StoreClosePage } from '@/pages/store-close';
import { MyReservationsPage } from '@/pages/my-reservations';
import { CheckoutPage } from '@/pages/checkout';
import { PaymentCompletePage } from '@/pages/payment-complete';
import { OfferDetailPage } from '@/pages/offer-detail';
import { TAB_BAR_HANDLE } from './handle';
import {
  OwnerOfferNewPlaceholder,
  OwnerOffersPlaceholder,
  OwnerTodayPlaceholder,
} from './placeholders';

export const routes: RouteObject[] = [
  {
    element: <CustomerLayout access="public" />,
    children: [
      { path: ROUTES.home, element: <HomePage />, handle: TAB_BAR_HANDLE },
      { path: ROUTE_PATTERNS.offerDetail, element: <OfferDetailPage /> },
    ],
  },
  {
    // A1~A3: 고객과 같은 420px 가운데 프레임. 가드·TabBar 없음(app-shell.md §12)
    element: <PublicFrameLayout />,
    children: [
      { path: ROUTES.login, element: <LoginPage /> },
      { path: ROUTES.signup, element: <SignupPage /> },
      { path: ROUTES.passwordReset, element: <PasswordResetPage /> },
    ],
  },
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
      // C5·C5b 내 예약(reservations 담당, design/frontend/reservations.md)
      { path: ROUTES.reservations, element: <MyReservationsPage />, handle: TAB_BAR_HANDLE },
      { path: ROUTES.me, element: <MyPage />, handle: TAB_BAR_HANDLE },
      { path: ROUTES.mePoints, element: <PointHistoryPage /> },
      { path: ROUTES.meWithdraw, element: <WithdrawPage /> },
      // 탭 바 없는 고객 전용 화면(결제 C3·C4, 예약 하위 화면)은 여기에 handle 없이 한 줄씩(customer-home.md §5.5)
      { path: ROUTE_PATTERNS.checkout, element: <CheckoutPage /> },
      { path: ROUTE_PATTERNS.paymentComplete, element: <PaymentCompletePage /> },
    ],
  },
  { path: ROUTES.owner, element: <Navigate to={ROUTES.ownerToday} replace /> },
  {
    element: <OwnerLayout />,
    children: [
      { path: ROUTES.ownerToday, element: <OwnerTodayPlaceholder />, handle: TAB_BAR_HANDLE },
      { path: ROUTES.ownerOffers, element: <OwnerOffersPlaceholder />, handle: TAB_BAR_HANDLE },
      { path: ROUTES.ownerOfferNew, element: <OwnerOfferNewPlaceholder /> },
      { path: ROUTES.ownerStore, element: <OwnerStorePage />, handle: TAB_BAR_HANDLE },
      { path: ROUTES.ownerStart, element: <OwnerStartPage /> },
      { path: ROUTES.ownerStoreClose, element: <StoreClosePage /> },
      { path: ROUTES.ownerProductNew, element: <ProductNewPage /> },
      { path: ROUTE_PATTERNS.ownerProduct, element: <ProductEditPage /> },
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
