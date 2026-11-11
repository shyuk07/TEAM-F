import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { createRef, useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { Overlay } from '@/shared/ui/Overlay';

function Frame({
  onClose = () => {},
  dismissible,
  returnFocusRef,
  startOpen = true,
}: {
  onClose?: () => void;
  dismissible?: boolean;
  returnFocusRef?: React.RefObject<HTMLElement | null>;
  startOpen?: boolean;
}) {
  const [open, setOpen] = useState(startOpen);
  return (
    <div className="app">
      <div className="bar" />
      <div className="body">
        <input aria-label="메모" />
        <button onClick={() => setOpen(true)}>열기</button>
        {open ? (
          <Overlay
            dismissible={dismissible}
            returnFocusRef={returnFocusRef}
            onClose={() => {
              onClose();
              setOpen(false);
            }}
          >
            <div role="dialog" aria-modal="true">
              <button>첫째</button>
              <button>둘째</button>
            </div>
          </Overlay>
        ) : null}
      </div>
      <div className="tabs" />
    </div>
  );
}
const app = () => document.querySelector('.app')!;
const body = () => document.querySelector<HTMLElement>('.body')!;

describe('Overlay', () => {
  it('자식이 .app 직계 .dim 안에 그려진다', () => {
    render(<Frame />);
    const dim = document.querySelector('.dim')!;
    expect(dim.parentElement).toBe(app());
    expect(dim).toContainElement(screen.getByRole('dialog'));
  });

  it('열림 동안 .body는 hidden이지만 마운트되어 입력값이 남는다', async () => {
    render(<Frame startOpen={false} />);
    await userEvent.type(screen.getByLabelText('메모'), '값');
    await userEvent.click(screen.getByRole('button', { name: '열기' }));
    expect(body().hidden).toBe(true);
    await userEvent.keyboard('{Escape}');
    expect(body().hidden).toBe(false);
    expect(screen.getByLabelText('메모')).toHaveValue('값');
  });

  it('Esc → onClose, dismissible=false면 호출하지 않는다', async () => {
    const onClose = vi.fn();
    const { unmount } = render(<Frame onClose={onClose} />);
    await userEvent.keyboard('{Escape}');
    expect(onClose).toHaveBeenCalledTimes(1);
    unmount();
    const off = vi.fn();
    render(<Frame onClose={off} dismissible={false} />);
    await userEvent.keyboard('{Escape}');
    expect(off).not.toHaveBeenCalled();
  });

  it('바깥(.dim) 클릭은 닫고 시트 안 클릭은 닫지 않는다', async () => {
    const onClose = vi.fn();
    render(<Frame onClose={onClose} />);
    await userEvent.click(screen.getByRole('button', { name: '첫째' }));
    expect(onClose).not.toHaveBeenCalled();
    await userEvent.click(document.querySelector('.dim')!);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it('dismissible=false면 바깥 클릭도 무시한다', async () => {
    const onClose = vi.fn();
    render(<Frame onClose={onClose} dismissible={false} />);
    await userEvent.click(document.querySelector('.dim')!);
    expect(onClose).not.toHaveBeenCalled();
  });

  it('열리면 첫 포커스 가능 요소에 포커스가 간다', () => {
    render(<Frame />);
    expect(screen.getByRole('button', { name: '첫째' })).toHaveFocus();
  });

  it('Tab·Shift+Tab이 시트 안에서만 돈다', async () => {
    render(<Frame />);
    await userEvent.tab();
    expect(screen.getByRole('button', { name: '둘째' })).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole('button', { name: '첫째' })).toHaveFocus();
    await userEvent.tab({ shift: true });
    expect(screen.getByRole('button', { name: '둘째' })).toHaveFocus();
  });

  it('닫히면 returnFocusRef 요소로 포커스가 간다', async () => {
    const ref = createRef<HTMLElement>();
    render(
      <div>
        <button
          ref={(el) => {
            (ref as { current: HTMLElement | null }).current = el;
          }}
        >
          대상
        </button>
        <Frame returnFocusRef={ref} />
      </div>,
    );
    await userEvent.keyboard('{Escape}');
    expect(screen.getByRole('button', { name: '대상' })).toHaveFocus();
  });

  it('returnFocusRef가 없으면 열기 전 activeElement로 돌아간다', async () => {
    render(<Frame startOpen={false} />);
    const open = screen.getByRole('button', { name: '열기' });
    await userEvent.click(open);
    await userEvent.keyboard('{Escape}');
    expect(open).toHaveFocus();
  });

  it('opener가 사라졌으면 프레임으로 포커스가 간다', async () => {
    function Gone() {
      const [stage, setStage] = useState<'btn' | 'open' | 'done'>('btn');
      return (
        <div className="app">
          <div className="body">
            {stage === 'btn' ? <button onClick={() => setStage('open')}>x</button> : null}
            {stage === 'open' ? (
              <Overlay onClose={() => setStage('done')}>
                <button>시트</button>
              </Overlay>
            ) : null}
          </div>
        </div>
      );
    }
    render(<Gone />);
    await userEvent.click(screen.getByRole('button', { name: 'x' }));
    await userEvent.keyboard('{Escape}');
    expect(app()).toHaveFocus();
  });

  it('열림 동안 .bar·.tabs는 inert, 닫히면 .dim·hidden·inert가 남지 않는다', async () => {
    const { unmount } = render(<Frame />);
    expect(document.querySelector('.bar')).toHaveAttribute('inert');
    expect(document.querySelector('.tabs')).toHaveAttribute('inert');
    await userEvent.keyboard('{Escape}');
    expect(document.querySelector('.dim')).toBeNull();
    expect(document.querySelector('[inert]')).toBeNull();
    expect(body().hidden).toBe(false);
    unmount();
  });

  it('언마운트해도 .dim·hidden·inert가 남지 않는다', () => {
    const { container, unmount } = render(<Frame />);
    const frameEl = container.querySelector('.app')!;
    expect(frameEl.querySelector('.dim')).not.toBeNull();
    unmount();
    expect(document.querySelector('.dim')).toBeNull();
  });
});
