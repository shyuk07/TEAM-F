import { useEffect, useId, useState } from 'react';
import type { Payment } from '../domain/payment';
import { usePay } from '../application/usePay';
import { formatWon } from '../domain/format';
import {
  POINT_ALL_LABEL,
  POINT_INPUT_LABEL,
  PROCESSING_LABEL,
  payErrorMessage,
  pointInputMessage,
} from '../domain/messages';
import { earnPreview, maxUsablePoint, payAmount, validatePointInput } from '../domain/point';

export type PaymentFormProps = {
  reservationId: string;
  productName: string;
  quantity: number;
  totalPrice: number;
  pointBalance: number;
  onPaid(payment: Payment): void;
  /** 결제 요청 처리 중 여부가 바뀔 때 알린다(page가 나가기·취소를 막는 데 씀). */
  onPendingChange?(pending: boolean): void;
};

// TODO: 적립 예정 포인트가 0이면 「결제 후 0P 적립」 줄을 숨긴다. 숨김은 임시 결정이다.
//   왜: states.md에 적립 0일 때 표시 정본이 없다 (docs/design/frontend/payments.md D-3)
//   언제: 결정 후 (사용자: 적립 0원 줄 숨김)
export function PaymentForm(props: PaymentFormProps) {
  const { reservationId, productName, quantity, totalPrice, pointBalance, onPaid } = props;
  const { onPendingChange } = props;
  const inputId = useId();
  const inputErrorId = useId();
  const [raw, setRaw] = useState('');
  const { pay, pending, error } = usePay();

  useEffect(() => {
    onPendingChange?.(pending);
  }, [pending, onPendingChange]);

  const point = validatePointInput(raw, pointBalance, totalPrice);
  const usePoint = point.error === null ? point.value : 0;
  const amount = payAmount(totalPrice, usePoint);
  const earn = earnPreview(amount);
  const inputMessage = pointInputMessage(point.error);
  const disabled = pending || point.error !== null;

  async function submit() {
    if (disabled) return;
    const payment = await pay({ reservationId, usePoint });
    if (payment !== null) onPaid(payment);
  }

  return (
    <>
      <div className="body">
        <div className="box">
          <div className="kv">
            <span>상품</span>
            <span>
              {productName} × {quantity}
            </span>
          </div>
          <div className="kv">
            <span>상품 금액</span>
            <span>{formatWon(totalPrice)}</span>
          </div>
          <div className="kv">
            <span>포인트</span>
            <span>−{formatWon(usePoint)}</span>
          </div>
          <div className="kv tot">
            <span>결제 금액</span>
            <span>{formatWon(amount)}</span>
          </div>
          {earn > 0 ? <div className="m">결제 후 {earn}P 적립 (1%)</div> : null}
        </div>
        <label className="lbl" htmlFor={inputId}>
          {POINT_INPUT_LABEL}
        </label>
        <div className="row">
          <input
            id={inputId}
            className="in"
            inputMode="numeric"
            aria-invalid={inputMessage !== null ? true : undefined}
            aria-describedby={inputMessage !== null ? inputErrorId : undefined}
            value={raw}
            onChange={(e) => setRaw(e.target.value)}
          />
          <button
            type="button"
            className="chip"
            onClick={() => setRaw(String(maxUsablePoint(pointBalance, totalPrice)))}
          >
            {POINT_ALL_LABEL}
          </button>
        </div>
        {inputMessage !== null ? (
          <div className="err" id={inputErrorId}>
            {inputMessage}
          </div>
        ) : null}
        {error !== null ? (
          <div className="err" role="alert">
            {payErrorMessage(error)}
          </div>
        ) : null}
      </div>
      <div className="cta">
        <button type="button" className="btn pri" disabled={disabled} onClick={() => void submit()}>
          {pending ? PROCESSING_LABEL : `결제하기 ${formatWon(amount)}`}
        </button>
      </div>
    </>
  );
}
