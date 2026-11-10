import { useState } from 'react';
import { canRefreshLocation, isValidRadiusKm, locationStatusLine } from '../domain/locationSheet';
import type { HomeOffers } from './useHomeOffers';

export type LocationSheetState = {
  isOpen: boolean;
  open(): void;
  close(): void;
  draftRadiusKm: number;
  selectRadius(km: number): void;
  apply(): void;
  statusLine: string;
  canUseCurrent: boolean;
  refreshLocation(): void;
};

export function useLocationSheet(
  home: Pick<HomeOffers, 'radiusKm' | 'setRadiusKm' | 'location'>,
): LocationSheetState {
  const [isOpen, setIsOpen] = useState(false);
  const [draft, setDraft] = useState(home.radiusKm);
  const status = home.location.status;
  const canUseCurrent = canRefreshLocation(status);

  return {
    isOpen,
    open() {
      setDraft(home.radiusKm);
      setIsOpen(true);
    },
    close() {
      setIsOpen(false);
    },
    draftRadiusKm: isOpen ? draft : home.radiusKm,
    selectRadius(km) {
      if (isValidRadiusKm(km)) setDraft(km);
    },
    apply() {
      if (!isOpen) return;
      if (draft !== home.radiusKm) home.setRadiusKm(draft);
      setIsOpen(false);
    },
    statusLine: locationStatusLine(status),
    canUseCurrent,
    refreshLocation() {
      if (canUseCurrent) home.location.retry();
    },
  };
}
