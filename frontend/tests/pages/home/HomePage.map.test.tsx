import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { routes } from '@/app/router/routes';
import { DEFAULT_MAP_CENTER, mapEmbedUrl } from '@/features/offers';
import { anonymousFakes, type AuthFakes } from '../../support/authFakes';
import { fixNow, restoreNow } from '../../support/clock';
import { renderRoutesWithAuth } from '../../support/renderWithAuth';
import { MANGWON } from '../../features/offers/fakes/fakeLocationProvider.fake';
import { makeNearby, makeOfferPage } from '../../features/offers/fakes/offers';

function renderHome(opts: { located?: boolean; path?: string; fakes?: AuthFakes } = {}) {
  const fakes = opts.fakes ?? anonymousFakes();
  if (opts.located) fakes.location.current.mockResolvedValue(MANGWON);
  fakes.offers.findNearby.mockResolvedValue(
    makeOfferPage([makeNearby({}, opts.located ? 0.42 : null)]),
  );
  return renderRoutesWithAuth(routes, { initialEntries: [opts.path ?? '/'], fakes });
}

async function openSheet(chipName: string) {
  await screen.findByRole('link', { name: /소금빵 세트/ });
  await userEvent.click(screen.getByRole('button', { name: chipName }));
  return screen.findByRole('dialog', { name: '어디서 찾을까요?' });
}

const lastOpts = (fakes: AuthFakes) => fakes.map.render.mock.calls.at(-1)?.[1];

describe('HomePage 위치 지도(C1a)', () => {
  beforeEach(() => fixNow());
  afterEach(() => restoreNow());

  it('시트를 열면 「지도」(role img)가 시트보다 앞이고 렌더러가 기기 위치·level 8로 호출된다', async () => {
    const { fakes } = renderHome({ located: true });
    const dialog = await openSheet('현재 위치 · 3km');
    const map = await screen.findByRole('img', { name: '지도' });
    expect(map.compareDocumentPosition(dialog) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    await waitFor(() =>
      expect(lastOpts(fakes)).toEqual({
        center: MANGWON,
        level: 8,
        radiusM: 3000,
        interactive: true,
      }),
    );
    expect(fakes.map.render.mock.calls.at(-1)?.[0]).toBe(map);
  });

  it('?radius=5면 level 8', async () => {
    const { fakes } = renderHome({ located: true, path: '/?radius=5' });
    await openSheet('현재 위치 · 5km');
    await screen.findByRole('img', { name: '지도' });
    await waitFor(() =>
      expect(lastOpts(fakes)).toEqual({
        center: MANGWON,
        level: 8,
        radiusM: 5000,
        interactive: true,
      }),
    );
  });

  it('시트에서 10km를 누르면 적용 전에도 render가 level 9·radiusM 10000으로 다시 호출되고 URL radius는 그대로', async () => {
    const { fakes, router } = renderHome({ located: true });
    const dialog = await openSheet('현재 위치 · 3km');
    await screen.findByRole('img', { name: '지도' });
    await waitFor(() => expect(lastOpts(fakes)).toMatchObject({ level: 8, radiusM: 3000 }));
    await userEvent.click(within(dialog).getByRole('button', { name: '10km' }));
    await waitFor(() =>
      expect(lastOpts(fakes)).toEqual({
        center: MANGWON,
        level: 9,
        radiusM: 10000,
        interactive: true,
      }),
    );
    expect(router.state.location.search).toBe('');
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('미리보기 10km 뒤 「적용」하면 URL ?radius=10', async () => {
    const { fakes, router } = renderHome({ located: true });
    const dialog = await openSheet('현재 위치 · 3km');
    await userEvent.click(within(dialog).getByRole('button', { name: '10km' }));
    await waitFor(() => expect(lastOpts(fakes)).toMatchObject({ radiusM: 10000 }));
    await userEvent.click(within(dialog).getByRole('button', { name: '적용' }));
    await waitFor(() => expect(router.state.location.search).toBe('?radius=10'));
  });

  it('적용 없이 닫았다 다시 열면 미리보기는 적용값(3km)부터', async () => {
    const { fakes } = renderHome({ located: true });
    const dialog = await openSheet('현재 위치 · 3km');
    await userEvent.click(within(dialog).getByRole('button', { name: '10km' }));
    await waitFor(() => expect(lastOpts(fakes)).toMatchObject({ radiusM: 10000 }));
    await userEvent.keyboard('{Escape}');
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: '현재 위치 · 3km' }));
    await screen.findByRole('dialog', { name: '어디서 찾을까요?' });
    await waitFor(() => expect(lastOpts(fakes)).toMatchObject({ level: 8, radiusM: 3000 }));
  });

  it('위치가 없으면 DEFAULT_MAP_CENTER로 호출된다', async () => {
    const { fakes } = renderHome();
    await openSheet('전체 지역');
    await screen.findByRole('img', { name: '지도' });
    await waitFor(() => expect(lastOpts(fakes)).toMatchObject({ center: DEFAULT_MAP_CENTER }));
  });

  it('지도가 있어도 바깥(.dim) 클릭으로 시트가 닫힌다', async () => {
    renderHome({ located: true });
    const dialog = await openSheet('현재 위치 · 3km');
    await screen.findByRole('img', { name: '지도' });
    await userEvent.click(dialog.closest('.dim') as HTMLElement);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.queryByRole('img', { name: '지도' })).not.toBeInTheDocument();
  });

  it('지도를 눌러도 시트가 열려 있고 URL이 그대로다', async () => {
    const { router } = renderHome({ located: true });
    await openSheet('현재 위치 · 3km');
    const map = await screen.findByRole('img', { name: '지도' });
    await userEvent.click(map);
    expect(screen.getByRole('dialog', { name: '어디서 찾을까요?' })).toBeInTheDocument();
    expect(screen.getByRole('img', { name: '지도' })).toBeInTheDocument();
    expect(router.state.location.search).toBe('');
  });

  it('폴백 iframe을 눌러도 시트가 열려 있다', async () => {
    const fakes = anonymousFakes();
    fakes.map.render.mockRejectedValue(new Error('no key'));
    renderHome({ located: true, fakes });
    await openSheet('현재 위치 · 3km');
    const frame = await screen.findByTitle('지도');
    await userEvent.click(frame);
    expect(screen.getByRole('dialog', { name: '어디서 찾을까요?' })).toBeInTheDocument();
    expect(screen.getByTitle('지도')).toBeInTheDocument();
  });

  it('렌더러가 실패하면 OSM iframe 폴백이 하나 보인다', async () => {
    const fakes = anonymousFakes();
    fakes.map.render.mockRejectedValue(new Error('no key'));
    renderHome({ located: true, fakes });
    await openSheet('현재 위치 · 3km');
    const frame = await screen.findByTitle('지도');
    expect(frame.tagName).toBe('IFRAME');
    expect(frame).toHaveAttribute('src', mapEmbedUrl(MANGWON, 3));
    expect(document.querySelectorAll('iframe')).toHaveLength(1);
    expect(screen.queryByRole('img', { name: '지도' })).not.toBeInTheDocument();
  });
});
