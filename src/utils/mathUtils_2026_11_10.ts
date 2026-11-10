/**
 * High-precision numerical math utilities and moving window statistics for TheRollerBlader.
 * Scheduled Milestone: Core Logic & Computation (2026-11-10).
 */

export function computeRunningStatistics(values: number[]): { mean: number; stdDev: number } {
  if (values.length === 0) return { mean: 0, stdDev: 0 };
  const n = values.length;
  const mean = values.reduce((acc, v) => acc + v, 0) / n;
  const variance = values.reduce((acc, v) => acc + Math.pow(v - mean, 2), 0) / (n > 1 ? n - 1 : 1);
  return { mean, stdDev: Math.sqrt(variance) };
}
