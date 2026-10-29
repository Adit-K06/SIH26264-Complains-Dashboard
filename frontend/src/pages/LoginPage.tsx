import { FormEvent, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  AlertCircle,
  ArrowRight,
  CheckCircle2,
  LockKeyhole,
  ShieldCheck,
  User,
} from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import { SyntheticFooter } from '../components/Shared'
import { errorMessage } from '../api/client'

const demoRoles = [
  { username: 'admin', label: 'Admin / Director', desc: 'National Headquarters (Full Access)' },
  { username: 'rb_officer', label: 'RB Officer', desc: 'Regulation Bureau' },
  { username: 'pgrc_officer', label: 'PGRC Officer', desc: 'Public Grievance Cell' },
  { username: 'regional_north', label: 'Regional Officer', desc: 'North Region Office' },
]

export function LoginPage() {
  const { ready, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('Demo@12345')
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  const returnTo = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? '/dashboard'

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setPending(true)
    try {
      await login(username, password)
      navigate(returnTo, { replace: true })
    } catch (reason) {
      setError(errorMessage(reason))
    } finally {
      setPending(false)
    }
  }

  function pickRole(u: string) {
    setUsername(u)
    setPassword('Demo@12345')
    setError('')
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-50 justify-between">
      {/* Top National Ribbon */}
      <div className="h-1.5 w-full bg-gradient-to-r from-orange-500 via-white to-emerald-600 shrink-0" />

      {/* Top Navigation Header */}
      <header className="px-6 py-4 flex items-center justify-between border-b border-slate-200 bg-white/80 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-blue-700 to-indigo-900 text-white font-extrabold text-xs shadow-md shadow-blue-500/20 border border-blue-400/30">
            AICTE
          </div>
          <div>
            <div className="text-[11px] font-bold text-blue-700 uppercase tracking-wider flex items-center gap-2">
              <span>All India Council for Technical Education</span>
              <span className="text-[9px] px-1.5 py-0.2 rounded font-mono font-medium bg-slate-100 text-slate-700 border border-slate-200">
                SIH-26264
              </span>
            </div>
            <div className="text-xs font-semibold text-slate-800">
              Integrated Complaint & Overlap Tracking Portal
            </div>
          </div>
        </div>
      </header>

      {/* Main Content Card */}
      <main className="flex flex-1 items-center justify-center px-4 py-8">
        <div className="grid w-full max-w-5xl overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-2xl md:grid-cols-[1.1fr_0.9fr]">
          {/* Left Hero Panel */}
          <section className="hidden flex-col justify-between bg-gradient-to-br from-[#0a1128] via-[#102b46] to-[#0f172a] p-10 text-white md:flex">
            <div>
              <div className="mb-8 flex items-center gap-3">
                <div className="flex items-center justify-center w-11 h-11 rounded-2xl bg-blue-600/30 border border-blue-400/30 text-white">
                  <ShieldCheck className="h-6 w-6 text-blue-400" />
                </div>
                <div>
                  <p className="text-sm font-extrabold tracking-wider text-blue-400 uppercase">AICTE CENTRAL HUB</p>
                  <p className="text-xs text-slate-300">Cross-Bureau Coordination Architecture</p>
                </div>
              </div>

              <div className="inline-block px-3 py-1 rounded-full bg-blue-500/20 border border-blue-400/30 text-[11px] font-bold text-blue-300 uppercase tracking-wider mb-4">
                Smart India Hackathon • SIH-26264
              </div>

              <h1 className="text-3xl font-extrabold leading-tight">
                Consolidated Monitoring Across All AICTE Bureaus & Cells.
              </h1>
              <p className="mt-4 text-xs sm:text-sm leading-6 text-slate-300 max-w-md">
                Eliminate duplicate inquiries, prevent conflicting show-cause notices between Regulation Bureau (RB) and PGRC, and enforce statutory 30-day resolution timelines.
              </p>

              <div className="mt-8 space-y-3 pt-6 border-t border-white/10">
                <div className="flex items-center gap-2 text-xs text-slate-300">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Two-Tier Overlap Engine (Campus-level & Semantic TF-IDF)</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-300">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Immutable Append-Only Audit Trail for all Officer Actions</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-300">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Whistleblower Privacy Protection via RBAC Backend Masking</span>
                </div>
              </div>
            </div>

            <div className="text-[11px] text-slate-400 pt-6">
              Authorized Government Personnel Only • Role-Based Access Control Active
            </div>
          </section>

          {/* Right Form Panel */}
          <section className="p-6 sm:p-10 flex flex-col justify-between">
            <div>
              <div className="mb-6">
                <span className="text-xs font-bold text-blue-700 uppercase tracking-wider">
                  Officer Access
                </span>
                <h2 className="mt-1 text-2xl font-extrabold text-slate-900">Sign In to Dashboard</h2>
                <p className="mt-1.5 text-xs text-slate-600">
                  Select a test officer role or enter authorized credentials.
                </p>
              </div>

              {/* Quick Role Fill Buttons */}
              <div className="mb-6">
                <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">
                  Quick Demo Role Switcher
                </p>
                <div className="grid grid-cols-2 gap-2">
                  {demoRoles.map((r) => {
                    const isSelected = username === r.username
                    return (
                      <button
                        key={r.username}
                        type="button"
                        onClick={() => pickRole(r.username)}
                        className={`text-left p-2.5 rounded-xl border text-xs transition cursor-pointer ${
                          isSelected
                            ? 'border-blue-500 bg-blue-50/80 text-blue-900 font-bold shadow-xs'
                            : 'border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-700'
                        }`}
                      >
                        <p className="font-bold truncate">{r.label}</p>
                        <p className="text-[10px] text-slate-500 truncate">{r.desc}</p>
                      </button>
                    )
                  })}
                </div>
              </div>

              {error && (
                <div
                  role="alert"
                  className="mb-5 flex gap-2 rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-800"
                >
                  <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              <form onSubmit={submit} className="space-y-4">
                <label className="block text-xs font-bold text-slate-700">
                  Username or Official Email
                  <div className="relative mt-1">
                    <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                    <input
                      autoComplete="username"
                      required
                      value={username}
                      onChange={(event) => setUsername(event.target.value)}
                      className="form-control pl-9 rounded-xl"
                      placeholder="admin"
                    />
                  </div>
                </label>

                <label className="block text-xs font-bold text-slate-700">
                  Password
                  <div className="relative mt-1">
                    <LockKeyhole className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                    <input
                      autoComplete="current-password"
                      type="password"
                      required
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      className="form-control pl-9 rounded-xl"
                      placeholder="••••••••••••"
                    />
                  </div>
                </label>

                <button
                  type="submit"
                  disabled={pending || !ready}
                  className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-xs font-bold text-white transition hover:bg-blue-700 shadow-md shadow-blue-500/25 disabled:cursor-not-allowed disabled:opacity-60 cursor-pointer active:scale-98"
                >
                  {pending ? 'Authenticating…' : 'Open Coordination Dashboard'}
                  {!pending && <ArrowRight className="h-4 w-4" />}
                </button>
              </form>
            </div>

            <div className="mt-6 rounded-xl bg-slate-50 p-3 text-xs text-slate-600 border border-slate-200">
              <p className="font-bold text-slate-800">Demo Credentials Pre-Loaded</p>
              <p className="mt-0.5 text-[11px]">
                Username: <code className="font-mono bg-white px-1 py-0.5 rounded border border-slate-200 font-bold">{username}</code> · Password: <code className="font-mono bg-white px-1 py-0.5 rounded border border-slate-200 font-bold">Demo@12345</code>
              </p>
            </div>
          </section>
        </div>
      </main>

      <SyntheticFooter />
    </div>
  )
}
