export type ReservationStatus = 'PENDING_PAYMENT' | 'RESERVED' | 'PICKED_UP' | 'CANCELLED';

export type CancelledBy = 'CUSTOMER' | 'STORE' | 'SYSTEM' | null;

export type Reservation = {
  id: string;
  offerId: string;
  storeName: string;
  productName: string;
  quantity: number;
  totalPrice: number;
  status: ReservationStatus;
  createdAt: Date;
  pickupCode: string;
  pickupAddress: string;
  cancelledBy: CancelledBy;
  pickupStart: Date;
  pickupEnd: Date;
  cancellableUntil: Date;
};

export type CreatedReservation = {
  id: string;
  offerId: string;
  quantity: number;
  unitPrice: number;
  totalPrice: number;
  status: ReservationStatus;
  createdAt: Date;
  storeName: string;
  productName: string;
};
