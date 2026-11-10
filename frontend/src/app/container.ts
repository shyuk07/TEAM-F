import { Container } from '@/shared/lib/di';
import { wireAuth } from '@/features/auth/wiring';

export function createContainer(): Container {
  return new Container([...wireAuth()]);
}
