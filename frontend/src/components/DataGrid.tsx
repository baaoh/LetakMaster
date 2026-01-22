import { Table } from 'react-bootstrap'

interface DataGridProps {
  data: any[]
}

export function DataGrid({ data }: DataGridProps) {
  if (!data || data.length === 0) {
    return <div className="text-muted text-center p-3">No data available</div>
  }

  // Extract columns from the first row's keys (assuming structure)
  // Our backend returns {ColName: {value: ..., formatting: ...}} per row
  // So we need to iterate keys of the row object.
  
  const sampleRow = data[0]
  const columns = Object.keys(sampleRow)

  // LIMIT RENDERING for performance. Preview mode only.
  const RENDER_LIMIT = 50
  const limitedData = data.slice(0, RENDER_LIMIT)
  const remaining = data.length - RENDER_LIMIT

  return (
    <div style={{ overflowX: 'auto' }}>
      <Table striped bordered hover size="sm">
        <thead>
          <tr>
            {columns.map(col => <th key={col}>{col}</th>)}
          </tr>
        </thead>
        <tbody>
          {limitedData.map((row, idx) => (
            <tr key={idx}>
              {columns.map(col => {
                const cell = row[col]
                if (!cell) return <td key={col}></td>
                
                // Optimized: No formatting rendering
                return <td key={col}>{cell.value}</td>
              })}
            </tr>
          ))}
        </tbody>
      </Table>
      {remaining > 0 && (
        <div className="p-2 text-center text-muted bg-light border-top">
            Showing first {RENDER_LIMIT} rows of {data.length}. 
            <strong> Open Master Excel to view full data.</strong>
        </div>
      )}
    </div>
  )
}
