import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { StatusTag } from '@/shared/ui';

describe('shared/ui StatusTag', () => {
  it.each([['ok' as const], ['hot' as const], ['mute' as const]])(
    '톤 %s면 tag ok|hot|mute 클래스를 쓴다',
    (tone) => {
      render(<StatusTag tone={tone}>영업 중</StatusTag>);
      expect(screen.getByText('영업 중')).toHaveClass('tag', tone);
    },
  );
});
