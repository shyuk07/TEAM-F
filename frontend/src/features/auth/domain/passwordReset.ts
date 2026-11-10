export function isResetCode(code: string): boolean {
  void code;
  throw new Error('not implemented: isResetCode');
}

export function canRequestReset(email: string): boolean {
  void email;
  throw new Error('not implemented: canRequestReset');
}

export function canConfirmReset(input: {
  codeSent: boolean;
  code: string;
  newPassword: string;
}): boolean {
  void input;
  throw new Error('not implemented: canConfirmReset');
}
