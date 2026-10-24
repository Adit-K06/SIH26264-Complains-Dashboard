// Mock data lives ONLY in src/api/mocks.
// THESE NUMBERS ARE FAKE PLACEHOLDERS (obvious round values) so the layout can be tested.
// They are NOT results of the matcher. The page shows a warning banner in mock mode.
export function mockEvaluation(): unknown {
  return {
    threshold: 0.5,
    metrics: { precision: 0.5, recall: 0.5, f1: 0.5 },
    confusion_matrix: { tp: 10, fp: 10, fn: 10, tn: 10 },
    baseline: {
      precision: 0.25,
      recall: 0.25,
      f1: 0.25,
      confusion_matrix: { tp: 5, fp: 15, fn: 15, tn: 5 },
    },
    false_positives: [
      { case_a: 'PLACEHOLDER-A', case_b: 'PLACEHOLDER-B', score: 0.5, reason: 'Placeholder example for layout testing' },
    ],
    missed_overlaps: [
      { case_a: 'PLACEHOLDER-C', case_b: 'PLACEHOLDER-D', score: 0.5, reason: 'Placeholder example for layout testing' },
    ],
    disclaimer: 'MOCK PLACEHOLDER. Real figures come from python -m app.ai.evaluate.',
  }
}
