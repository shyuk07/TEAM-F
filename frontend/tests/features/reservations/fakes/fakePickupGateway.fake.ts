import { vi } from 'vitest';
import type { PickupGateway } from '@/features/reservations';

export class FakePickupGateway implements PickupGateway {
  pickup = vi.fn<PickupGateway['pickup']>((reservationId, code) =>
    Promise.resolve({
      id: reservationId,
      pickupCode: code,
      status: 'PICKED_UP',
      pickedUpAt: new Date(),
    }),
  );
}
