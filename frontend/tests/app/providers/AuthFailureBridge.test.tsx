import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { AuthFailureBridge } from '@/app/providers/AuthFailureBridge';
import { notifyAuthFailure } from '@/shared/api/authFailure';
import { createAuthContainer, anonymousFakes } from '../../support/authFakes';
import { DepsProvider } from '@/shared/lib/DepsProvider';

type AuthFakes = ReturnType<typeof anonymousFakes>;

function renderBridge(fakes: AuthFakes) {
  render(
    <DepsProvider container={createAuthContainer(fakes)}>
      <AuthFailureBridge />
    </DepsProvider>,
  );
  return fakes;
}

describe('app/providers AuthFailureBridge', () => {
  it('마운트 후 notifyAuthFailure() → FakeSessionStore.clear 1번', () => {
    const fakes = renderBridge(anonymousFakes());
    notifyAuthFailure();
    expect(fakes.session.clear).toHaveBeenCalledTimes(1);
  });

  it('언마운트 후에는 불려도 clear가 안 불린다', () => {
    const fakes = anonymousFakes();
    const { unmount } = render(
      <DepsProvider container={createAuthContainer(fakes)}>
        <AuthFailureBridge />
      </DepsProvider>,
    );
    unmount();
    notifyAuthFailure();
    expect(fakes.session.clear).not.toHaveBeenCalled();
  });

  it('다시 마운트해도 한 번만 불린다(중복 등록 없음)', () => {
    const fakes = anonymousFakes();
    const first = render(
      <DepsProvider container={createAuthContainer(fakes)}>
        <AuthFailureBridge />
      </DepsProvider>,
    );
    first.unmount();
    renderBridge(fakes);
    expect(screen.queryByRole('alert')).toBeNull();
    notifyAuthFailure();
    notifyAuthFailure();
    expect(fakes.session.clear).toHaveBeenCalledTimes(1);
  });
});
