import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import type { RouteObject } from 'react-router';
import { OwnerLayout } from '@/app/layouts/OwnerLayout';
import { ROUTES } from '@/shared/lib/routes';
import { ownerUser } from '../../features/auth/fakes/users';
import { signedInFakes } from '../../support/authFakes';
import { renderRoutesWithOwnerStore } from '../../support/renderWithOwnerStore';
import { FakeStoreRepository } from '../../entities/store/fakes/fakeStoreRepository.fake';
import { activeStore, closedStore, suspendedStore } from '../../entities/store/fakes/stores';

function repoReturning(store: typeof activeStore | null) {
  const repo = new FakeStoreRepository();
  repo.findMine.mockResolvedValue(store);
  return repo;
}

type AuthFakes = ReturnType<typeof signedInFakes>;

function renderGate(
  fakes: AuthFakes,
  repo: FakeStoreRepository,
  initial: string = ROUTES.ownerToday,
) {
  const routes: RouteObject[] = [
    { path: '/login', element: <p>로그인 화면</p> },
    { path: '/', element: <p>홈 화면</p> },
    {
      element: <OwnerLayout />,
      children: [
        {
          path: '/owner/today',
          element: <p>O1 내용</p>,
          handle: { tabBar: true },
        },
        { path: '/owner/offers', element: <p>O2 내용</p>, handle: { tabBar: true } },
        { path: '/owner/store', element: <p>O4 내용</p>, handle: { tabBar: true } },
        { path: '/owner/start', element: <p>O0 내용</p> },
        { path: '/owner/store/close', element: <p>O7 내용</p> },
      ],
    },
  ];
  return renderRoutesWithOwnerStore(routes, {
    initialEntries: [initial],
    fakes,
    repo,
  });
}

const fakes = () => signedInFakes(ownerUser);

describe('app/layouts OwnerStoreGate', () => {
  it('조회 중에는 aria-busy 프레임만 있고 Outlet 내용이 없다', async () => {
    const repo = new FakeStoreRepository();
    repo.findMine.mockReturnValue(new Promise(() => {}));
    renderGate(fakes(), repo);
    expect(screen.queryByText('O1 내용')).toBeNull();
    expect(document.querySelector('[aria-busy="true"]')).not.toBeNull();
  });

  it('상점이 없고 /owner/today면 /owner/start로 이동한다(Outlet 내용 안 보임)', async () => {
    const { router } = renderGate(fakes(), repoReturning(null));
    await waitFor(() => expect(router.state.location.pathname).toBe(ROUTES.ownerStart));
    expect(screen.queryByText('O1 내용')).toBeNull();
  });

  it('상점이 없고 /owner/start면 리다이렉트 없이 O0 내용이 보인다', async () => {
    const { router } = renderGate(fakes(), repoReturning(null), ROUTES.ownerStart);
    expect(await screen.findByText('O0 내용')).toBeInTheDocument();
    expect(router.state.location.pathname).toBe(ROUTES.ownerStart);
  });

  it('상점 ACTIVE + /owner/start는 /owner/today로 보낸다', async () => {
    const { router } = renderGate(fakes(), repoReturning(activeStore), ROUTES.ownerStart);
    await waitFor(() => expect(router.state.location.pathname).toBe(ROUTES.ownerToday));
  });

  it('상점 ACTIVE + /owner/store는 TabBar를 포함해 보인다', async () => {
    renderGate(fakes(), repoReturning(activeStore), ROUTES.ownerStore);
    expect(await screen.findByText('O4 내용')).toBeInTheDocument();
    expect(document.querySelector('.tabs')).not.toBeNull();
  });

  it('상점 SUSPENDED + /owner/start는 /owner/today로 보낸다', async () => {
    const { router } = renderGate(fakes(), repoReturning(suspendedStore), ROUTES.ownerStart);
    await waitFor(() => expect(router.state.location.pathname).toBe(ROUTES.ownerToday));
  });

  it('상점 SUSPENDED + /owner/store는 보인다', async () => {
    renderGate(fakes(), repoReturning(suspendedStore), ROUTES.ownerStore);
    expect(await screen.findByText('O4 내용')).toBeInTheDocument();
  });

  it('상점 CLOSED + /owner/store/close는 /owner/start로 보낸다', async () => {
    const { router } = renderGate(fakes(), repoReturning(closedStore), ROUTES.ownerStoreClose);
    await waitFor(() => expect(router.state.location.pathname).toBe(ROUTES.ownerStart));
  });

  it('상점 CLOSED + /owner/start는 보인다', async () => {
    renderGate(fakes(), repoReturning(closedStore), ROUTES.ownerStart);
    expect(await screen.findByText('O0 내용')).toBeInTheDocument();
  });

  it('조회 오류면 오류 문구 + 「다시 시도」가 있고 누르면 findMine을 다시 부른다', async () => {
    const repo = new FakeStoreRepository();
    repo.findMine
      .mockRejectedValueOnce(new Error('종료된 상태입니다.'))
      .mockResolvedValue(activeStore);
    renderGate(fakes(), repo);
    expect(await screen.findByRole('alert')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: '다시 시도' }));
    await waitFor(() => expect(repo.findMine.mock.calls.length).toBeGreaterThan(1));
    expect(await screen.findByText('O1 내용')).toBeInTheDocument();
  });

  it('오류 메시지가 비면 상점 조회 실패 기본 문구(MY_STORE_ERROR_FALLBACK_MESSAGE)를 보인다', async () => {
    const repo = new FakeStoreRepository();
    repo.findMine.mockRejectedValueOnce(new Error(''));
    renderGate(fakes(), repo);
    expect(
      await screen.findByText('상점 정보를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.'),
    ).toBeInTheDocument();
  });

  it('같은 계정에서 /owner/today ↔ /owner/store 이동은 findMine을 다시 부르지 않는다', async () => {
    const { router, repo } = renderGate(fakes(), repoReturning(activeStore));
    await screen.findByText('O1 내용');
    const calls = repo.findMine.mock.calls.length;
    router.navigate(ROUTES.ownerStore);
    await screen.findByText('O4 내용');
    expect(repo.findMine.mock.calls.length).toBe(calls);
    router.navigate(ROUTES.ownerToday);
    await screen.findByText('O1 내용');
    expect(repo.findMine.mock.calls.length).toBe(calls);
  });
});
