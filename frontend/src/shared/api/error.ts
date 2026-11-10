export class ApiError extends Error {
  constructor(
    public status: number,
    public errorCode: string,
    message: string,
  ) {
    super(message);
  }
}

export async function toApiError(res: Response): Promise<ApiError> {
  const body: unknown = await res.json().catch(() => null);
  if (body && typeof body === 'object') {
    const b = body as { error_code?: unknown; message?: unknown };
    if (typeof b.error_code === 'string') {
      return new ApiError(res.status, b.error_code, String(b.message ?? ''));
    }
  }
  return new ApiError(res.status, 'UNKNOWN', res.statusText);
}
