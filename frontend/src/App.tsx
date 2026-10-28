/**
 * App.tsx — P0 stub.
 * Just renders a health-check page until P11 wires the full router.
 */
function App() {
  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center gap-4 p-8">
      <div className="text-center space-y-3 max-w-lg">
        <div className="text-4xl font-bold text-primary">AICTE</div>
        <h1 className="text-xl font-semibold text-foreground">
          Complaint Coordination Dashboard
        </h1>
        <p className="text-sm text-muted-foreground">
          SIH26264 — P0 scaffold loaded. Full UI comes in P11.
        </p>
        <p className="text-xs text-muted-foreground border-t border-border pt-3 mt-3">
          Demo uses synthetic data. SLA values are placeholders, not official AICTE norms.
        </p>
      </div>
    </div>
  )
}

export default App
