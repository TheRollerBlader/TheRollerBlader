/**
 * Resilient API streaming client with exponential backoff for TheRollerBlader.
 * Scheduled Milestone: Integration & Data Ingest (2026-11-12).
 */

export interface RequestOptions {
  timeoutMs?: number;
  maxRetries?: number;
}

export async function fetchWithRetry<T>(url: string, options: RequestOptions = {}): Promise<T | null> {
  const timeoutMs = options.timeoutMs ?? 5000;
  const maxRetries = options.maxRetries ?? 3;
  let backoff = 500;

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      const controller = new AbortController();
      const id = setTimeout(() => controller.abort(), timeoutMs);
      const res = await fetch(url, { signal: controller.signal });
      clearTimeout(id);
      if (res.ok) {
        return (await res.json()) as T;
      }
    } catch {
      if (attempt < maxRetries) {
        await new Promise(r => setTimeout(r, backoff));
        backoff *= 2;
      }
    }
  }
  return null;
}
