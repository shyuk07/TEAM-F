export type StoreReservationStatus = 'PENDING_PAYMENT' | 'RESERVED' | 'PICKED_UP' | 'CANCELLED';

export type StoreReservation = {
  id: string;
  productName: string;
  quantity: number;
  totalPrice: number;
  status: StoreReservationStatus;
  createdAt: Date;
};

export type StoreReservationPage = {
  items: StoreReservation[];
  page: number;
  size: number;
  total: number;
};
