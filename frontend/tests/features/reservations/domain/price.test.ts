import { reservationTotalPrice } from '@/features/reservations/domain/price';

it.each([
  [3000, 1, 3000],
  [2300, 5, 11500],
  [0, 5, 0],
])('예약 단가 %i원과 수량 %i개의 총액은 %i원이다', (unitPrice, quantity, expected) => {
  expect(reservationTotalPrice(unitPrice, quantity)).toBe(expected);
});
