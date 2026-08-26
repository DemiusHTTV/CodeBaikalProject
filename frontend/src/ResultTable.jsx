const MAX_VISIBLE_ROWS = 50

function formatCell(value) {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'boolean') return value ? 'да' : 'нет'
  return String(value)
}

export default function ResultTable({ columns, rows }) {
  if (!columns.length) return null

  const visible = rows.slice(0, MAX_VISIBLE_ROWS)

  return (
    <div className="result-table-wrap">
      <table className="result-table">
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {visible.map((row, rowIndex) => (
            <tr key={rowIndex}>
              {row.map((cell, cellIndex) => (
                <td key={cellIndex}>{formatCell(cell)}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {rows.length > MAX_VISIBLE_ROWS && (
        <p className="result-more">
          Показаны первые {MAX_VISIBLE_ROWS} строк из {rows.length}.
        </p>
      )}
    </div>
  )
}
