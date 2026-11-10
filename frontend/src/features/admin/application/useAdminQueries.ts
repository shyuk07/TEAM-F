import { useDep } from '@/shared/lib/di';
import { useAsync } from '@/shared/lib/useAsync';
import { queryKey, type UserListQuery } from '../domain/userQuery';
import { AdminRepositoryToken } from './tokens';

/** version이 바뀌면 다시 불러온다(다른 화면 부품에서 회원 상태를 바꾼 뒤). */
export function useUserList(q: UserListQuery, version = 0) {
  const admin = useDep(AdminRepositoryToken);
  return useAsync((signal) => admin.listUsers(q, signal), `${queryKey(q)}#${version}`);
}

export function useUserDetail(id: string) {
  const admin = useDep(AdminRepositoryToken);
  return useAsync((signal) => admin.findUser(id, signal), id);
}

export function useUserPoints(id: string, size: number) {
  const admin = useDep(AdminRepositoryToken);
  return useAsync((signal) => admin.findUserPoints(id, 1, size, signal), `${id}|${size}`);
}
