export function canSubmitLogin(email: string, password: string): boolean {
  return email.trim() !== '' && password !== '';
}
