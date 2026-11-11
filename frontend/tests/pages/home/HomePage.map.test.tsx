import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { routes } from '@/app/router/routes';
import { anonymousFakes } from '../../support/authFakes';
import { fixNow, restoreNow } from '../../support/clock';
import { renderRoutesWithAuth } from '../../support/renderWithAuth';
import { MANGWON } from '../../features/offers/fakes/fakeLocationProvider.fake';
import { makeNearby, makeOfferPage } from '../../features/offers/fakes/offers';

function renderHome(opts: { located?: boolean; path?: string } = {}) {
  const fakes = anonymousFakes();
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

const params = (frame: HTMLElement) => new URL(frame.getAttribute('src')!).searchParams;

describe('HomePage 위치 지도(C1a)', () => {
  beforeEach(() => fixNow());
  afterEach(() => restoreNow());

  it('시트를 열면 「지도」 iframe이 시트보다 앞에 있고 기기 위치 marker(반경 3km bbox)', async () => {
    renderHome({ located: true });
    const dialog = await openSheet('현재 위치 · 3km');
    const frame = await screen.findByTitle('지도');
    expect(frame.tagName).toBe('IFRAME');
    expect(frame.compareDocumentPosition(dialog) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(params(frame).get('marker')).toBe('37.55600,126.90100');
    expect(params(frame).get('bbox')).toBe('126.86691,37.52897,126.93509,37.58303');
  });

  it('?radius=5면 bbox가 5km 범위', async () => {
    renderHome({ located: true, path: '/?radius=5' });
    await openSheet('현재 위치 · 5km');
    const frame = await screen.findByTitle('지도');
    expect(params(frame).get('bbox')).toBe('126.84418,37.51095,126.95782,37.60105');
  });

  it('위치가 없으면 DEFAULT_MAP_CENTER marker', async () => {
    renderHome();
    await openSheet('전체 지역');
    const frame = await screen.findByTitle('지도');
    expect(params(frame).get('marker')).toBe('37.55630,126.90200');
  });

  it('지도가 있어도 바깥(.dim) 클릭으로 시트가 닫힌다', async () => {
    renderHome({ located: true });
    const dialog = await openSheet('현재 위치 · 3km');
    await screen.findByTitle('지도');
    await userEvent.click(dialog.closest('.dim') as HTMLElement);
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.queryByTitle('지도')).not.toBeInTheDocument();
  });
});
