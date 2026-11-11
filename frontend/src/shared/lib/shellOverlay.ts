// TODO: 오버레이 동안 .cta를 숨기고 .tabs는 남긴다. 정본이 화면별로 정하면 맞춘다.
//   왜: wireframe마다 .tabs 유무가 달라 의도가 불명이다 (app-shell.md C-11, D-19)
//   언제: 결정 후 (사용자: 오버레이 동안 탭·CTA 표시)
// 앱 프레임(.app)의 본문(.body) 자리를 오버레이(.dim)가 대신하게 하는 DOM 도우미(app-shell.md §11.4).
// React를 모르고 업무도 모른다.
// 제약(app-shell.md D-31·D-32): 한 프레임에 오버레이를 둘 이상 동시에 열지 않는다(중첩은 지원하는 사용이 아님).
// 열 때 이미 hidden인 요소는 숨김 목록에 넣지 않으므로 닫을 때 되살리지 않는다.

export type ShellOverlayHandle = {
  // 포털 대상으로 쓰는 .dim 요소(마지막 직계 .body 바로 뒤에 만들어진다)
  readonly dim: HTMLElement;
  // 닫기: observer 해제 → .dim 제거 → hidden·inert 해제 → scrollTop 복원 → 그다음 포커스 복귀
  close(returnFocusTo?: HTMLElement | null): void;
};

type FrameState = {
  count: number;
  hidden: HTMLElement[];
  scrolls: Map<HTMLElement, number>;
  inerted: Element[];
  observer: MutationObserver;
};

const frames = new WeakMap<Element, FrameState>();

function directChildren(frame: Element, selector: string): HTMLElement[] {
  return Array.from(frame.querySelectorAll<HTMLElement>(`:scope > ${selector}`));
}

// 숨김은 hidden 속성만 쓴다. bundle.css의 [hidden] 규칙이 .body·.cta의 display를 덮어 숨긴다.
function hide(state: FrameState, el: HTMLElement) {
  if (el.hidden) return;
  state.hidden.push(el);
  if (el.classList.contains('body')) state.scrolls.set(el, el.scrollTop);
  el.hidden = true;
}

function openState(frame: Element): FrameState {
  const existing = frames.get(frame);
  if (existing) return existing;
  const state: FrameState = {
    count: 0,
    hidden: [],
    scrolls: new Map(),
    inerted: [],
    observer: new MutationObserver(() => {
      for (const body of directChildren(frame, '.body')) hide(state, body);
    }),
  };
  for (const el of [...directChildren(frame, '.body'), ...directChildren(frame, '.cta')]) {
    hide(state, el);
  }
  for (const el of directChildren(frame, '.bar, .tabs, .nav')) {
    el.setAttribute('inert', '');
    state.inerted.push(el);
  }
  state.observer.observe(frame, { childList: true });
  frames.set(frame, state);
  return state;
}

function releaseState(frame: Element, state: FrameState) {
  state.observer.disconnect();
  for (const el of state.hidden) el.hidden = false;
  for (const el of state.inerted) el.removeAttribute('inert');
  for (const [el, top] of state.scrolls) el.scrollTop = top;
  frames.delete(frame);
}

export function openShellOverlay(anchor: Element): ShellOverlayHandle {
  const frame = anchor.closest('.app');
  const dim = document.createElement('div');
  dim.className = 'dim';
  if (frame === null) {
    document.body.appendChild(dim);
    return {
      dim,
      close(returnFocusTo) {
        dim.remove();
        if (returnFocusTo?.isConnected) returnFocusTo.focus({ preventScroll: true });
      },
    };
  }
  const state = openState(frame);
  state.count += 1;
  const bodies = directChildren(frame, '.body');
  const lastBody = bodies[bodies.length - 1];
  if (lastBody) {
    lastBody.after(dim);
  } else {
    const before = frame.querySelector(':scope > .cta, :scope > .tabs');
    if (before) before.before(dim);
    else frame.appendChild(dim);
  }
  let closed = false;
  return {
    dim,
    close(returnFocusTo) {
      if (closed) return;
      closed = true;
      dim.remove();
      state.count -= 1;
      if (state.count === 0) releaseState(frame, state);
      if (returnFocusTo?.isConnected) {
        returnFocusTo.focus({ preventScroll: true });
      } else if (frame.isConnected && state.count === 0) {
        (frame as HTMLElement).tabIndex = -1;
        (frame as HTMLElement).focus({ preventScroll: true });
      }
    },
  };
}
