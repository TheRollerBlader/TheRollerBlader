/**
 * Status indicator and visual health telemetry components for TheRollerBlader.
 * Scheduled Milestone: UI & Visualization Components (2026-11-11).
 */

export interface ComponentHealthStatus {
  componentId: string;
  healthy: boolean;
  latencyMs: number;
  lastUpdated: string;
}

export function formatHealthBadge(status: ComponentHealthStatus): string {
  const tag = status.healthy ? 'HEALTHY' : 'DEGRADED';
  return `[${tag}] ${status.componentId} - ${status.latencyMs.toFixed(1)}ms (${status.lastUpdated})`;
}

export function renderAsciiSparkline(values: number[], width = 16): string {
  if (values.length === 0) return '---';
  const ticks = [' ', '▂', '▃', '▄', '▅', '▆', '▇', '█'];
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  return values
    .slice(-width)
    .map(v => ticks[Math.min(ticks.length - 1, Math.floor(((v - min) / range) * (ticks.length - 1)))])
    .join('');
}
