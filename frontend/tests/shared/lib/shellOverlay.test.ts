import { afterEach, describe, expect, it, vi } from 'vitest';
import { openShellOverlay } from '@/shared/lib/shellOverlay';

function frame(parts: string[] = ['bar', 'body', 'cta', 'tabs']) {
  const app = document.createElement('div');
  app.className = 'app';
  for (const p of parts) {
    const el = document.createElement('div');
    el.className = p;
    app.appendChild(el);
  }
  document.body.appendChild(app);
  return app;
}
const order = (app: Element) => Array.from(app.children).map((c) => c.className);

afterEach(() => {
  document.body.innerHTML = '';
});

describe('openShellOverlay', () => {
  it('열면 직계 .body가 hidden이고 .dim이 .body 바로 뒤에 온다', () => {
    const app = frame();
    openShellOverlay(app.querySelector('.body')!);
    expect(app.querySelector<HTMLElement>('.body')!.hidden).toBe(true);
    expect(order(app)).toEqual(['bar', 'body', 'dim', 'cta', 'tabs']);
  });

  it('.cta는 hidden, .bar·.tabs는 inert이고 .tabs는 hidden이 아니다', () => {
    const app = frame();
    openShellOverlay(app.querySelector('.body')!);
    expect(app.querySelector<HTMLElement>('.cta')!.hidden).toBe(true);
    expect(app.querySelector('.bar')).toHaveAttribute('inert');
    expect(app.querySelector('.tabs')).toHaveAttribute('inert');
    expect(app.querySelector<HTMLElement>('.tabs')!.hidden).toBe(false);
  });

  it('열린 동안에도 인라인 style.display를 쓰지 않는다', () => {
    const app = frame();
    const h = openShellOverlay(app.querySelector('.body')!);
    expect(app.querySelector<HTMLElement>('.body')!.style.display).toBe('');
    expect(app.querySelector<HTMLElement>('.cta')!.style.display).toBe('');
    h.close();
  });

  it('닫으면 .dim이 사라지고 hidden·inert가 모두 풀린다', () => {
    const app = frame();
    const h = openShellOverlay(app.querySelector('.body')!);
    h.close();
    expect(app.querySelector('.dim')).toBeNull();
    expect(app.querySelector<HTMLElement>('.body')!.hidden).toBe(false);
    expect(app.querySelector<HTMLElement>('.body')!.style.display).toBe('');
    expect(app.querySelector<HTMLElement>('.cta')!.hidden).toBe(false);
    expect(app.querySelector('[inert]')).toBeNull();
  });

  it('닫으면 열기 전 .body.scrollTop을 복원한다', () => {
    const app = frame();
    const body = app.querySelector<HTMLElement>('.body')!;
    body.scrollTop = 120;
    const h = openShellOverlay(body);
    body.scrollTop = 0;
    h.close();
    expect(body.scrollTop).toBe(120);
  });

  it('열린 동안 추가된 .body도 hidden이 된다', async () => {
    const app = frame();
    const h = openShellOverlay(app.querySelector('.body')!);
    const added = document.createElement('div');
    added.className = 'body';
    app.appendChild(added);
    await Promise.resolve();
    expect(added.hidden).toBe(true);
    h.close();
    expect(added.hidden).toBe(false);
  });

  it('.body가 없으면 .dim이 .cta 앞, 둘 다 없으면 끝에 들어간다', () => {
    const a = frame(['bar', 'cta', 'tabs']);
    openShellOverlay(a.querySelector('.bar')!);
    expect(order(a)).toEqual(['bar', 'dim', 'cta', 'tabs']);
    const b = frame(['bar']);
    openShellOverlay(b.querySelector('.bar')!);
    expect(order(b)).toEqual(['bar', 'dim']);
  });

  it('직계가 아닌 .body는 숨기지 않는다', () => {
    const app = frame();
    const nested = document.createElement('div');
    nested.className = 'body';
    app.querySelector('.bar')!.appendChild(nested);
    openShellOverlay(app.querySelector('.body')!);
    expect(nested.hidden).toBe(false);
  });

  it('오버레이 둘 중 하나만 닫으면 hidden이 유지되고 마지막을 닫으면 풀린다(방어, 지원하는 사용 아님)', () => {
    const app = frame();
    const body = app.querySelector<HTMLElement>('.body')!;
    const h1 = openShellOverlay(body);
    const h2 = openShellOverlay(body);
    h1.close();
    expect(body.hidden).toBe(true);
    h2.close();
    expect(body.hidden).toBe(false);
  });

  it('.app이 없으면 document.body에 .dim을 붙이고 아무것도 숨기지 않는다', () => {
    const lone = document.createElement('div');
    document.body.appendChild(lone);
    const h = openShellOverlay(lone);
    expect(h.dim.parentElement).toBe(document.body);
    expect(lone.hidden).toBe(false);
    h.close();
    expect(document.querySelector('.dim')).toBeNull();
  });

  it('닫은 뒤 returnFocusTo로 포커스가 돌아간다(숨김 해제 후)', () => {
    const app = frame();
    const btn = document.createElement('button');
    app.querySelector('.body')!.appendChild(btn);
    const h = openShellOverlay(btn);
    h.close(btn);
    expect(btn).toHaveFocus();
  });

  it('열기 전 이미 hidden인 .body는 닫은 뒤에도 hidden이고 다른 .body는 복원된다', () => {
    const app = frame(['bar', 'body', 'body', 'cta']);
    const [first, second] = Array.from(app.querySelectorAll<HTMLElement>('.body'));
    first.hidden = true;
    const h = openShellOverlay(second);
    h.close();
    expect(first.hidden).toBe(true);
    expect(second.hidden).toBe(false);
  });

  it('열기 전 이미 hidden인 .cta는 닫은 뒤에도 hidden이다', () => {
    const app = frame();
    const cta = app.querySelector<HTMLElement>('.cta')!;
    cta.hidden = true;
    const h = openShellOverlay(app.querySelector('.body')!);
    h.close();
    expect(cta.hidden).toBe(true);
    expect(app.querySelector<HTMLElement>('.body')!.hidden).toBe(false);
  });

  it('포커스 복귀는 preventScroll: true로 부른다', () => {
    const app = frame();
    const btn = document.createElement('button');
    app.querySelector('.body')!.appendChild(btn);
    const spy = vi.spyOn(btn, 'focus');
    const h = openShellOverlay(btn);
    h.close(btn);
    expect(spy).toHaveBeenCalledWith({ preventScroll: true });
  });
});
