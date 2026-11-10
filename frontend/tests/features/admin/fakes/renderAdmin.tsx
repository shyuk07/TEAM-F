import type { ReactNode } from 'react';
import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { AdminRepositoryToken } from '@/features/admin';
import { Container, bind } from '@/shared/lib/di';
import { DepsProvider } from '@/shared/lib/DepsProvider';
import { FakeAdminRepository } from './fakeAdminRepository.fake';

/** 가짜 AdminRepository를 넣은 컨테이너 + 라우터 + 앱 프레임(.app)으로 감싸 그린다. rerender해도 감싼 것이 유지된다. */
export function renderAdmin(ui: ReactNode, repo = new FakeAdminRepository()) {
  const container = new Container([bind(AdminRepositoryToken, repo)]);
  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <DepsProvider container={container}>
        <MemoryRouter>
          <div className="app">{children}</div>
        </MemoryRouter>
      </DepsProvider>
    );
  }
  const result = render(ui, { wrapper: Wrapper });
  return { ...result, repo };
}
