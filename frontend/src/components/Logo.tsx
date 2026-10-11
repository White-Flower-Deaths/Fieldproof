import type { ReactNode } from 'react'

export function Logo({
  tagline,
  href,
}: {
  tagline?: string
  href?: string
}) {
  const content = (
    <>
      <svg className="fp-logo__mark" viewBox="0 0 32 32" aria-hidden="true">
        <path
          d="M16 2.5 4.5 6.9v8.3c0 7.3 4.8 12.5 11.5 14.4 6.7-1.9 11.5-7.1 11.5-14.4V6.9L16 2.5Z"
          fill="currentColor"
          opacity="0.14"
        />
        <path
          d="M16 2.5 4.5 6.9v8.3c0 7.3 4.8 12.5 11.5 14.4 6.7-1.9 11.5-7.1 11.5-14.4V6.9L16 2.5Z"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinejoin="round"
        />
        <path
          d="m10.8 16.4 3.6 3.6 7-7.6"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.4"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <span className="fp-logo__text">
        <span className="fp-logo__word">FieldProof</span>
        {tagline ? <span className="fp-logo__tagline">{tagline}</span> : null}
      </span>
    </>
  )

  if (href) {
    return (
      <a className="fp-logo" href={href} aria-label="FieldProof home">
        {content}
      </a>
    )
  }
  return <span className="fp-logo">{content}</span>
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: ReactNode
  subtitle?: ReactNode
  actions?: ReactNode
}) {
  return (
    <header className="fp-page-header">
      <div>
        <h1 className="fp-page-header__title">{title}</h1>
        {subtitle ? <p className="fp-page-header__subtitle">{subtitle}</p> : null}
      </div>
      {actions ? <div className="fp-page-header__actions">{actions}</div> : null}
    </header>
  )
}
