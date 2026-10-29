import { FormEvent, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { AlertCircle, ArrowRight, GraduationCap, LockKeyhole } from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import { SyntheticFooter } from '../components/Shared'
import { errorMessage, useMocks } from '../api/client'

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

  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      <main className="flex flex-1 items-center justify-center px-4 py-10">
        <div className="grid w-full max-w-5xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-xl md:grid-cols-[1.05fr_0.95fr]">
          <section className="hidden flex-col justify-between bg-[#102b46] p-10 text-white md:flex">
            <div>
              <div className="mb-10 flex items-center gap-3"><div className="grid h-12 w-12 place-items-center rounded-xl bg-teal-600"><GraduationCap className="h-7 w-7" /></div><div><p className="text-sm font-bold tracking-wide">AICTE COORDINATION</p><p className="text-xs text-slate-300">Complaint dashboard</p></div></div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-teal-300">One coordination view</p>
              <h1 className="mt-3 text-3xl font-bold leading-tight">Track complaint work across bureaus and cells.</h1>
              <p className="mt-4 max-w-sm text-sm leading-6 text-slate-300">Review case progress, due dates, and potential overlaps in one clear workspace.</p>
            </div>
            <p className="text-xs text-slate-300">For authorized AICTE officers</p>
          </section>
          <section className="p-6 sm:p-10">
            <div className="mb-7 flex items-center gap-3 md:hidden"><div className="grid h-10 w-10 place-items-center rounded-lg bg-[#102b46] text-white"><GraduationCap className="h-6 w-6" /></div><div><p className="text-sm font-bold text-slate-900">AICTE COORDINATION</p><p className="text-xs text-slate-500">Complaint dashboard</p></div></div>
            <div className="mb-7"><p className="text-sm font-semibold text-teal-800">Officer access</p><h2 className="mt-1 text-2xl font-bold text-slate-900">Sign in</h2><p className="mt-2 text-sm text-slate-600">Use your demo account to open the coordination dashboard.</p></div>
            {error && <div role="alert" className="mb-5 flex gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />{error}</div>}
            <form onSubmit={submit} className="space-y-4">
              <label className="block text-sm font-semibold text-slate-700">Username or email<input autoComplete="username" required value={username} onChange={(event) => setUsername(event.target.value)} className="form-control mt-1.5" placeholder="admin" /></label>
              <label className="block text-sm font-semibold text-slate-700">Password<div className="relative mt-1.5"><LockKeyhole className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" /><input autoComplete="current-password" type="password" required value={password} onChange={(event) => setPassword(event.target.value)} className="form-control pl-10" placeholder="Enter your password" /></div></label>
              <button disabled={pending || !ready} className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-[#102b46] px-4 py-3 text-sm font-semibold text-white transition hover:bg-[#183f63] disabled:cursor-not-allowed disabled:opacity-60">{pending ? 'Signing in…' : 'Sign in'}{!pending && <ArrowRight className="h-4 w-4" />}</button>
            </form>
            {useMocks && <div className="mt-6 rounded-lg bg-slate-50 p-3 text-xs text-slate-600"><p className="font-semibold text-slate-800">Demo Login (Auto-Filled)</p><p className="mt-1">Username: admin · Password: Demo@12345</p></div>}
          </section>
        </div>
      </main>
      <SyntheticFooter />
    </div>
  )
}
