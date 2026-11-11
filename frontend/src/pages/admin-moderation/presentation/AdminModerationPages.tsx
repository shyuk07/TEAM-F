import { ModerationPanel } from '@/features/admin';

// M5 상점 탭
export function AdminStoresPage() {
  return <ModerationPanel target="store" />;
}

// M5 할인 탭
export function AdminOffersPage() {
  return <ModerationPanel target="offer" />;
}
