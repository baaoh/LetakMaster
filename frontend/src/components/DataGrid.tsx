import { Table, Badge } from 'react-bootstrap'

interface DataGridProps {
  data: any[]
}

export function DataGrid({ data }: DataGridProps) {
  if (!data || !Array.isArray(data) || data.length === 0) {
    return <div className="text-muted text-center p-5">No product data found.</div>
  }

  // Detect Format: 
  // High-Fidelity: { page: 1, full_data: { A: {header: '...', value: '...'}, ... } }
  // Legacy: { page: 1, A: 'value', B: 'value' ... }
  const firstRow = data[0]
  const isHighFidelity = !!firstRow.full_data
  
  let columnLetters: string[] = []
  let headers: Record<string, string> = {}

  if (isHighFidelity) {
    const fullData = firstRow.full_data || {}
    columnLetters = Object.keys(fullData).sort((a, b) => {
        if (a.length !== b.length) return a.length - b.length;
        return a.localeCompare(b);
    })
    columnLetters.forEach(col => {
        headers[col] = fullData[col]?.header || col
    })
  } else {
    // Legacy support: Just get all keys that look like columns
    columnLetters = Object.keys(firstRow).filter(k => k.length <= 2 && /^[A-Z]+$/.test(k)).sort((a, b) => {
        if (a.length !== b.length) return a.length - b.length;
        return a.localeCompare(b);
    })
    columnLetters.forEach(col => {
        headers[col] = col
    })
  }

  const RENDER_LIMIT = 100
  const limitedData = data.slice(0, RENDER_LIMIT)
  const remaining = data.length - RENDER_LIMIT

  return (
    <div style={{ height: '100%', overflow: 'auto' }}>
      <Table striped bordered hover size="sm" className="mb-0" style={{ fontSize: '0.75rem', whiteSpace: 'nowrap' }}>
        <thead className="sticky-top bg-light shadow-sm" style={{ zIndex: 10 }}>
          <tr>
            <th className="bg-dark text-white text-center">Pg</th>
            <th className="bg-dark text-white">Product Name</th>
            {columnLetters.map(col => (
              <th key={col} title={headers[col]}>
                <div className="text-muted" style={{ fontSize: '0.6rem' }}>{col}</div>
                <div className="text-truncate" style={{ maxWidth: '120px' }}>{headers[col]}</div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {limitedData.map((row, idx) => {
            const rowData = isHighFidelity ? (row.full_data || {}) : row
            return (
              <tr key={idx}>
                <td className="text-center fw-bold bg-light"><Badge bg="secondary">{row.page || '?'}</Badge></td>
                <td className="fw-bold">{row.product_name || row.V || 'Unknown'}</td>
                {columnLetters.map(col => {
                  const cell = rowData[col]
                  const val = isHighFidelity ? (cell ? cell.value : '') : cell
                  return <td key={col} className="text-truncate" style={{ maxWidth: '180px' }} title={String(val)}>
                    {val === null || val === undefined ? '' : String(val)}
                  </td>
                })}
              </tr>
            )
          })}
        </tbody>
      </Table>
      {remaining > 0 && (
        <div className="p-3 text-center text-muted bg-warning bg-opacity-10 border-top sticky-bottom">
            Showing first {RENDER_LIMIT} rows of {data.length}. 
        </div>
      )}
    </div>
  )
}
