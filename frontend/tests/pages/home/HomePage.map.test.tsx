import { screen, waitFor } from '@testing-library/react';
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

  it('시트를 열면 「지도」(role img)가 시트보다 앞이고 렌더러가 기기 위치·level 6으로 호출된다', async () => {
    const { fakes } = renderHome({ located: true });
    const dialog = await openSheet('현재 위치 · 3km');
    const map = await screen.findByRole('img', { name: '지도' });
    expect(map.compareDocumentPosition(dialog) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    await waitFor(() => expect(lastOpts(fakes)).toEqual({ center: MANGWON, level: 6 }));
    expect(fakes.map.render.mock.calls.at(-1)?.[0]).toBe(map);
  });

  it('?radius=5면 level 7', async () => {
    const { fakes } = renderHome({ located: true, path: '/?radius=5' });
    await openSheet('현재 위치 · 5km');
    await screen.findByRole('img', { name: '지도' });
    await waitFor(() => expect(lastOpts(fakes)).toEqual({ center: MANGWON, level: 7 }));
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
