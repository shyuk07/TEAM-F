import { Link, useNavigate } from 'react-router';
import { useOwnerStore } from '@/entities/store';
import { StoreCloseForm } from '@/features/stores';
import { ROUTES } from '@/shared/lib/routes';
import { AppBar } from '@/shared/ui';

// O7 상점 폐점 확인(stores.md §5). 조회 중에는 아무것도 그리지 않고, 상점이 있으면
// 폼을 그린다. 폐점 성공·충돌 재조회는 StoreCloseForm 안의 useCloseStore가 맡는다.
export function StoreClosePage() {
  const store = useOwnerStore();
  const navigate = useNavigate();

  if (store === null) return null;

  return (
    <>
      <AppBar
        title="상점 폐점"
        left={
          <Link to={ROUTES.ownerStore} aria-label="뒤로">
            ←
          </Link>
        }
      />
      <StoreCloseForm store={store} onCancel={() => navigate(ROUTES.ownerStore)} />
    </>
  );
}
