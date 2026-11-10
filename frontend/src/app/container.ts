import { Container } from '@/shared/lib/di';
import { wireAdmin } from '@/features/admin/wiring';
import { wireAuth } from '@/features/auth/wiring';

export function createContainer(): Container {
  return new Container([...wireAuth(), ...wireAdmin()]);
}
