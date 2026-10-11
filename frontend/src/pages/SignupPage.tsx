import { useState } from 'react'
import type { FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { UserPlus } from 'lucide-react'
import { useAuth } from '../auth/auth-context'
import {
  Alert,
  Button,
  Card,
  CardBody,
  CardHeader,
  Logo,
  TextField,
} from '../components'
import './pages.css'

export default function SignupPage() {
  const { user, ready, register } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  if (ready && user) return <Navigate to="/" replace />

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)
    if (password !== confirm) {
      setError('Passwords do not match.')
      return
    }
    setSubmitting(true)
    try {
      await register(username.trim(), password)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sign-up failed.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fp-shell">
      <div className="fp-container fp-auth">
        <aside className="fp-auth__panel" aria-label="About FieldProof">
          <span className="fp-auth__panel-stripe" aria-hidden="true" />
          <div>
            <p className="fp-auth__panel-title">FieldProof</p>
            <p className="fp-auth__panel-tag">
              Explainable colourimetric field testing with tamper-evident records.
            </p>
          </div>
          <ul className="fp-auth__panel-specs">
            <li>
              <span>Records</span>
              <b>ECDSA P-256 + SHA-256 chain</b>
            </li>
            <li>
              <span>Colour</span>
              <b>sRGB to CIELAB, CIEDE2000</b>
            </li>
            <li>
              <span>Analysis</span>
              <b>Explainable scoring engine</b>
            </li>
            <li>
              <span>Result</span>
              <b>Presumptive only</b>
            </li>
          </ul>
          <p className="fp-auth__panel-foot">
            Not a substitute for laboratory confirmation.
          </p>
        </aside>
        <div className="fp-auth__card">
          <div className="fp-auth__brand">
            <Logo tagline="signed field test records" />
          </div>
          <Card raised>
            <CardHeader
              title="Operator sign-up"
              subtitle="Creates a field-officer account; records you sign are attributed to you."
            />
            <CardBody>
              <form className="fp-auth__form" onSubmit={onSubmit} noValidate>
                {error ? <Alert tone="danger" title="Sign-up failed">{error}</Alert> : null}
                <TextField
                  label="Operator ID"
                  name="username"
                  autoComplete="username"
                  hint="3-32 characters: letters, digits, dot, dash or underscore."
                  required
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                />
                <TextField
                  label="Password"
                  name="password"
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  hint="At least 8 characters."
                  required
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                />
                <TextField
                  label="Confirm password"
                  name="password_confirm"
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  required
                  value={confirm}
                  onChange={(event) => setConfirm(event.target.value)}
                />
                <Button
                  type="submit"
                  size="lg"
                  fullWidth
                  loading={submitting}
                  iconBefore={<UserPlus size={18} />}
                >
                  Create account
                </Button>
              </form>

              <p className="fp-auth__switch">
                Already have an account? <Link to="/login">Sign in</Link>
              </p>
            </CardBody>
          </Card>
        </div>
      </div>
    </div>
  )
}
