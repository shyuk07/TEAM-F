import { request } from '@/shared/api/client';
import type { Offer } from '../domain/offer';
import type {
  DeactivateInput,
  DeactivateResult,
  NewOffer,
  OfferChanges,
  OfferCommands,
  StockAdjustResult,
} from '../domain/offerCommands';
import { type OfferDto, toOffer, toStatus } from './offerDto';

type DeactivateResponseDto = {
  offer: OfferDto;
  cancelled_reservation_count: number;
};

type StockAdjustResponseDto = {
  offer_id: string;
  initial_stock: number;
  remaining_stock: number;
  is_sold_out: boolean;
  status: string;
  log_id: string;
};

export class HttpOfferCommands implements OfferCommands {
  async register(productId: string, input: NewOffer, signal?: AbortSignal): Promise<Offer> {
    const body: Record<string, unknown> = {
      sale_price: input.salePrice,
      initial_stock: input.initialStock,
      sales_end: input.salesEnd.toISOString(),
      pickup_start: input.pickupStart.toISOString(),
      pickup_end: input.pickupEnd.toISOString(),
    };
    if (input.salesStart !== undefined) {
      body.sales_start = input.salesStart.toISOString();
    }

    const dto = await request<OfferDto>(`/v1/products/${encodeURIComponent(productId)}/offers`, {
      method: 'POST',
      body,
      signal,
    });
    return toOffer(dto);
  }

  async relist(offerId: string, input: NewOffer, signal?: AbortSignal): Promise<Offer> {
    const body: Record<string, unknown> = {
      sale_price: input.salePrice,
      initial_stock: input.initialStock,
      sales_end: input.salesEnd.toISOString(),
      pickup_start: input.pickupStart.toISOString(),
      pickup_end: input.pickupEnd.toISOString(),
    };
    if (input.salesStart !== undefined) {
      body.sales_start = input.salesStart.toISOString();
    }

    const dto = await request<OfferDto>(`/v1/offers/${encodeURIComponent(offerId)}/relist`, {
      method: 'POST',
      body,
      signal,
    });
    return toOffer(dto);
  }

  async update(offerId: string, changes: OfferChanges, signal?: AbortSignal): Promise<Offer> {
    const body: Record<string, unknown> = {};
    if (changes.salePrice !== undefined) {
      body.sale_price = changes.salePrice;
    }
    if (changes.initialStock !== undefined) {
      body.initial_stock = changes.initialStock;
    }
    if (changes.salesEnd !== undefined) {
      body.sales_end = changes.salesEnd.toISOString();
    }
    if (changes.pickupStart !== undefined) {
      body.pickup_start = changes.pickupStart.toISOString();
    }
    if (changes.pickupEnd !== undefined) {
      body.pickup_end = changes.pickupEnd.toISOString();
    }

    const dto = await request<OfferDto>(`/v1/offers/${encodeURIComponent(offerId)}`, {
      method: 'PATCH',
      body,
      signal,
    });
    return toOffer(dto);
  }

  async deactivate(
    offerId: string,
    input: DeactivateInput,
    signal?: AbortSignal,
  ): Promise<DeactivateResult> {
    const dto = await request<DeactivateResponseDto>(
      `/v1/offers/${encodeURIComponent(offerId)}/deactivate`,
      {
        method: 'POST',
        body: {
          reason: input.reason,
          cancel_reservations: input.cancelReservations,
        },
        signal,
      },
    );
    return {
      offer: toOffer(dto.offer),
      cancelledCount: dto.cancelled_reservation_count,
    };
  }

  async adjustStock(
    offerId: string,
    amount: number,
    reason?: string,
    signal?: AbortSignal,
  ): Promise<StockAdjustResult> {
    const dto = await request<StockAdjustResponseDto>(
      `/v1/offers/${encodeURIComponent(offerId)}/stock-adjustments`,
      {
        method: 'POST',
        body: {
          amount,
          reason: reason?.trim() ? reason.trim() : undefined,
        },
        signal,
      },
    );
    return {
      remainingStock: dto.remaining_stock,
      isSoldOut: dto.is_sold_out,
      status: toStatus(dto.status),
    };
  }
}
