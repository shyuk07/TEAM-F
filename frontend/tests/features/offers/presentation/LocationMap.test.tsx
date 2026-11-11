import { render, screen, waitFor } from '@testing-library/react';
import { LocationMap, MapRendererToken, mapEmbedUrl } from '@/features/offers';
import { Container, bind } from '@/shared/lib/di';
import { DepsProvider } from '@/shared/lib/DepsProvider';
import { FakeMapRenderer } from '../fakes/fakeMapRenderer.fake';

const center = { lat: 37.5563, lng: 126.902 };
const other = { lat: 37.556, lng: 126.901 };
type Props = { center: typeof center; radiusKm: 1 | 3 | 5 | 10 };

function renderMap(props: Props, map = new FakeMapRenderer()) {
  const container = new Container([bind(MapRendererToken, map)]);
  const ui = (p: Props) => (
    <DepsProvider container={container}>
      <LocationMap {...p} />
    </DepsProvider>
  );
  const result = render(ui(props));
  return { map, ...result, rerenderWith: (p: Props) => result.rerender(ui(p)) };
}

describe('LocationMap', () => {
  it('감싸는 요소 없이 div role=img 「지도」 하나(마우스 이벤트 받음, flex 1, width 100%)', () => {
    const { container } = renderMap({ center, radiusKm: 3 });
    const el = screen.getByRole('img', { name: '지도' });
    expect(el.tagName).toBe('DIV');
    expect(container.children).toHaveLength(1);
    expect(container.firstElementChild).toBe(el);
    expect(el.style.pointerEvents).not.toBe('none');
    expect(getComputedStyle(el).pointerEvents).not.toBe('none');
    expect(el.style.flex).toMatch(/^1(\s|$)/);
    expect(el.style.width).toBe('100%');
  });

  it('그 div에 render(el, { center, level: 8, radiusM: 3000, interactive: true }, signal)을 호출한다', async () => {
    const { map } = renderMap({ center, radiusKm: 3 });
    const el = screen.getByRole('img', { name: '지도' });
    await waitFor(() => expect(map.render).toHaveBeenCalledTimes(1));
    const [target, opts, signal] = map.render.mock.calls[0]!;
    expect(target).toBe(el);
    expect(opts).toEqual({ center, level: 8, radiusM: 3000, interactive: true });
    expect(signal).toBeInstanceOf(AbortSignal);
  });

  it('center·radius가 바뀌면 다시 호출한다', async () => {
    const { map, rerenderWith } = renderMap({ center, radiusKm: 3 });
    await waitFor(() => expect(map.render).toHaveBeenCalledTimes(1));
    rerenderWith({ center, radiusKm: 10 });
    await waitFor(() => expect(map.render).toHaveBeenCalledTimes(2));
    expect(map.render.mock.calls[1]![1]).toEqual({
      center,
      level: 9,
      radiusM: 10000,
      interactive: true,
    });
    rerenderWith({ center: other, radiusKm: 10 });
    await waitFor(() => expect(map.render).toHaveBeenCalledTimes(3));
    expect(map.render.mock.calls[2]![1]).toEqual({
      center: other,
      level: 9,
      radiusM: 10000,
      interactive: true,
    });
  });

  it('언마운트하면 signal이 abort된다', async () => {
    const { map, unmount } = renderMap({ center, radiusKm: 3 });
    await waitFor(() => expect(map.render).toHaveBeenCalledTimes(1));
    const signal = map.render.mock.calls[0]![2]!;
    expect(signal.aborted).toBe(false);
    unmount();
    expect(signal.aborted).toBe(true);
  });

  it('render가 reject하면 div 대신 OSM iframe(title 「지도」, tabIndex -1, 마우스 이벤트 받음)', async () => {
    const map = new FakeMapRenderer();
    map.render.mockRejectedValue(new Error('no key'));
    const { container } = renderMap({ center, radiusKm: 5 }, map);
    const frame = await screen.findByTitle('지도');
    expect(frame.tagName).toBe('IFRAME');
    expect(frame).toHaveAttribute('src', mapEmbedUrl(center, 5));
    expect(frame.tabIndex).toBe(-1);
    expect(frame.style.pointerEvents).not.toBe('none');
    expect(getComputedStyle(frame).pointerEvents).not.toBe('none');
    expect(screen.queryByRole('img', { name: '지도' })).not.toBeInTheDocument();
    expect(container.children).toHaveLength(1);
  });
});
