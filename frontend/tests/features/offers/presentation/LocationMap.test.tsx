import { render, screen } from '@testing-library/react';
import { LocationMap, mapEmbedUrl } from '@/features/offers';

const center = { lat: 37.5563, lng: 126.902 };

describe('LocationMap', () => {
  it('감싸는 요소 없이 iframe 하나(title 「지도」, src = mapEmbedUrl)', () => {
    const { container } = render(<LocationMap center={center} radiusKm={3} />);
    const frame = screen.getByTitle('지도');
    expect(frame.tagName).toBe('IFRAME');
    expect(container.children).toHaveLength(1);
    expect(container.firstElementChild).toBe(frame);
    expect(frame).toHaveAttribute('src', mapEmbedUrl(center, 3));
  });

  it('보기 전용: tabIndex -1, pointer-events none, flex 1로 영역을 채운다', () => {
    render(<LocationMap center={center} radiusKm={5} />);
    const frame = screen.getByTitle('지도');
    expect(frame.tabIndex).toBe(-1);
    expect(frame.style.pointerEvents).toBe('none');
    expect(frame.style.flex).toMatch(/^1(\s|$)/);
  });
});
