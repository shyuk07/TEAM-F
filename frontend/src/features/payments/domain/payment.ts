// 백엔드 enum 값을 reference가 나열하지 않아 string으로 둔다 (docs/design/frontend/payments.md C-3)
export type PaymentStatus = string;

export type Payment = {
  id: string;
  reservationId: string;
  amount: number;
  status: PaymentStatus;
  paidAt: Date | null;
};
