import type { ReactNode } from 'react'

export type Column<T> = {
  key: string
  header: ReactNode
  render?: (row: T) => ReactNode
  numeric?: boolean
}

export function DataTable<T>({
  columns,
  rows,
  getRowKey,
  className,
  caption,
}: {
  columns: Column<T>[]
  rows: T[]
  getRowKey?: (row: T, index: number) => string
  className?: string
  caption?: string
}) {
  const classes = ['fp-table', className ?? ''].filter(Boolean).join(' ')
  return (
    <div className="fp-table-wrap">
      <table className={classes}>
        {caption ? <caption className="sr-only">{caption}</caption> : null}
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.key}
                scope="col"
                className={column.numeric ? 'is-numeric' : undefined}
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={getRowKey ? getRowKey(row, index) : index}>
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={column.numeric ? 'is-numeric' : undefined}
                >
                  {column.render ? column.render(row) : String((row as Record<string, unknown>)[column.key] ?? '')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
