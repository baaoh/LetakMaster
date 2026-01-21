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

  return (
    <div style={{ overflowX: 'auto' }}>
      <Table striped bordered hover size="sm">
        <thead>
          <tr>
            {columns.map(col => <th key={col}>{col}</th>)}
          </tr>
        </thead>
        <tbody>
          {data.map((row, idx) => (
            <tr key={idx}>
              {columns.map(col => {
                const cell = row[col]
                // cell has {value, formatting}
                const style = cell.formatting ? {
                  fontWeight: cell.formatting.bold ? 'bold' : 'normal',
                  backgroundColor: cell.formatting.color || 'inherit',
                  border: cell.formatting.border ? '1px solid #000' : '1px solid #dee2e6'
                } : {}
                
                return <td key={col} style={style}>{cell.value}</td>
              })}
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  )
}
