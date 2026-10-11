import type { InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from 'react'
import { useId } from 'react'

/* ------------------------------------------------------------------ Field */

export type FieldProps = {
  label: ReactNode
  hint?: ReactNode
  error?: ReactNode
  required?: boolean
  htmlFor?: string
  children: ReactNode
}

export function Field({ label, hint, error, required, htmlFor, children }: FieldProps) {
  return (
    <div className="fp-field">
      <label className="fp-field__label" htmlFor={htmlFor}>
        {label}
        {required ? (
          <span className="fp-field__required" aria-hidden="true">
            *
          </span>
        ) : null}
      </label>
      {children}
      {error ? (
        <span className="fp-field__error" role="alert">
          {error}
        </span>
      ) : hint ? (
        <span className="fp-field__hint">{hint}</span>
      ) : null}
    </div>
  )
}

/** Convenience wrapper: Field + input in one, auto-generated id. */
export function TextField({
  label,
  hint,
  error,
  required,
  mono,
  ...rest
}: Omit<InputHTMLAttributes<HTMLInputElement>, 'id'> & {
  label: ReactNode
  hint?: ReactNode
  error?: ReactNode
  mono?: boolean
}) {
  const id = useId()
  return (
    <Field label={label} hint={hint} error={error} required={required} htmlFor={id}>
      <input
        id={id}
        className={mono ? 'fp-input fp-input--mono' : 'fp-input'}
        aria-invalid={error ? true : undefined}
        aria-describedby={hint && !error ? `${id}-hint` : undefined}
        required={required}
        {...rest}
      />
    </Field>
  )
}

export function TextAreaField({
  label,
  hint,
  error,
  required,
  ...rest
}: Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, 'id'> & {
  label: ReactNode
  hint?: ReactNode
  error?: ReactNode
}) {
  const id = useId()
  return (
    <Field label={label} hint={hint} error={error} required={required} htmlFor={id}>
      <textarea
        id={id}
        className="fp-textarea"
        aria-invalid={error ? true : undefined}
        required={required}
        {...rest}
      />
    </Field>
  )
}

export function SelectField({
  label,
  hint,
  error,
  required,
  children,
  ...rest
}: SelectHTMLAttributes<HTMLSelectElement> & {
  label: ReactNode
  hint?: ReactNode
  error?: ReactNode
  children: ReactNode
}) {
  const id = useId()
  return (
    <Field label={label} hint={hint} error={error} required={required} htmlFor={id}>
      <select id={id} className="fp-select" aria-invalid={error ? true : undefined} {...rest}>
        {children}
      </select>
    </Field>
  )
}

export function Checkbox({
  label,
  hint,
  disabled,
  ...rest
}: Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> & {
  label: ReactNode
  hint?: ReactNode
}) {
  return (
    <label
      className={['fp-checkbox', disabled ? 'fp-checkbox--disabled' : '']
        .filter(Boolean)
        .join(' ')}
    >
      <input type="checkbox" disabled={disabled} {...rest} />
      <span className="fp-checkbox__text">
        <span>{label}</span>
        {hint ? <span className="fp-checkbox__hint">{hint}</span> : null}
      </span>
    </label>
  )
}
