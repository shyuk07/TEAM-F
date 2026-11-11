import { useCallback, useState } from 'react';
import { SessionStoreToken } from '@/entities/session';
import { useDep } from '@/shared/lib/di';
import type { ErrorInfo } from './errorInfo';
import { confirmPasswordReset, requestPasswordReset } from './passwordReset';
import { AccountGatewayToken } from './tokens';
import { useSubmit } from './useSubmit';

type ConfirmArgs = { email: string; code: string; newPassword: string };

export function usePasswordReset(): {
  sentEmail: string | null;
  request(email: string): Promise<void>;
  resend(): Promise<void>;
  confirm(code: string, newPassword: string): Promise<boolean>;
  invalidate(): void;
  requestPending: boolean;
  requestError: ErrorInfo | null;
  confirmPending: boolean;
  confirmError: ErrorInfo | null;
} {
  const account = useDep(AccountGatewayToken);
  const session = useDep(SessionStoreToken);
  const [sentEmail, setSentEmail] = useState<string | null>(null);

  // 성공하면 보낸(정리된) 이메일을 돌려줘 실패(undefined)와 구분한다.
  const requestSubmit = useSubmit<string, string>(async (email, signal) => {
    const trimmed = email.trim();
    await requestPasswordReset({ account }, trimmed, signal);
    return trimmed;
  });
  const confirmSubmit = useSubmit<ConfirmArgs, true>(async (input, signal) => {
    await confirmPasswordReset({ account, session }, input, signal);
    return true;
  });

  const submitRequest = requestSubmit.submit;
  const submitConfirm = confirmSubmit.submit;
  const resetConfirm = confirmSubmit.reset;

  const request = useCallback(
    async (email: string): Promise<void> => {
      const sent = await submitRequest(email);
      if (sent !== undefined) setSentEmail(sent);
    },
    [submitRequest],
  );

  // 60초 안이면 서버가 새 코드를 만들지 않지만 응답은 같다. 화면은 차이를 표시하지 않는다(auth-account.md D-24).
  const resend = useCallback(async (): Promise<void> => {
    if (sentEmail === null) return;
    await request(sentEmail);
  }, [request, sentEmail]);

  // 확인은 코드를 보낸 이메일로만 한다(다른 이메일의 코드로 확인하는 실수 방지, D-24).
  const confirm = useCallback(
    async (code: string, newPassword: string): Promise<boolean> => {
      if (sentEmail === null) return false;
      return (await submitConfirm({ email: sentEmail, code, newPassword })) === true;
    },
    [sentEmail, submitConfirm],
  );

  const invalidate = useCallback(() => {
    setSentEmail(null);
    resetConfirm();
  }, [resetConfirm]);

  return {
    sentEmail,
    request,
    resend,
    confirm,
    invalidate,
    requestPending: requestSubmit.state.pending,
    requestError: requestSubmit.state.error,
    confirmPending: confirmSubmit.state.pending,
    confirmError: confirmSubmit.state.error,
  };
}
