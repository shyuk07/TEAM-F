export const DEACTIVATE_REASON_MAX = 200;

export type DeactivateIssue = 'reason-empty' | 'reason-too-long';

export function validateDeactivate(input: { reason: string }): DeactivateIssue | null {
  const trimmed = input.reason.trim();
  if (!trimmed) {
    return 'reason-empty';
  }
  if (trimmed.length > DEACTIVATE_REASON_MAX) {
    return 'reason-too-long';
  }
  return null;
}
