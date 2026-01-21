import { useState, useEffect } from 'react'
import { Container, Row, Col, Card, Button, Form, Table, ListGroup, Badge } from 'react-bootstrap'
import axios from 'axios'

const API_BASE = 'http://localhost:8000'

interface SourceFile {
  id: number
  filename: string
  uploaded_at: string
}

interface SourceData {
  id: number
  row_index: number
  column_name: string
  value: string
  formatting_json: string
}

function App() {
  const [sourceFiles, setSourceFiles] = useState<SourceFile[]>([])
  const [selectedFile, setSelectedFile] = useState<number | null>(null)
  const [sourceData, setSourceData] = useState<SourceData[]>([])
  const [uploadFile, setUploadFile] = useState<File | null>(null)

  useEffect(() => {
    fetchSourceFiles()
  }, [])

  const fetchSourceFiles = async () => {
    try {
      const resp = await axios.get(`${API_BASE}/source-files`)
      setSourceFiles(resp.data)
    } catch (err) {
      console.error("Failed to fetch source files", err)
    }
  }

  const handleUpload = async () => {
    if (!uploadFile) return
    const formData = new FormData()
    formData.append('file', uploadFile)
    try {
      await axios.post(`${API_BASE}/upload/excel`, formData)
      setUploadFile(null)
      fetchSourceFiles()
    } catch (err) {
      console.error("Upload failed", err)
    }
  }

  const viewFileData = async (fileId: number) => {
    setSelectedFile(fileId)
    try {
      const resp = await axios.get(`${API_BASE}/source-files/${fileId}/data`)
      setSourceData(resp.data)
    } catch (err) {
      console.error("Failed to fetch data", err)
    }
  }

  // Group data by row index for table display
  const rows = sourceData.reduce((acc: any, item) => {
    if (!acc[item.row_index]) acc[item.row_index] = {}
    acc[item.row_index][item.column_name] = item.value
    return acc
  }, {})

  const columns = Array.from(new Set(sourceData.map(d => d.column_name)))

  return (
    <Container fluid className="py-4">
      <h1 className="mb-4">LetakMaster Dashboard</h1>
      
      <Row>
        <Col md={4}>
          <Card className="mb-4">
            <Card.Header>Upload New Data</Card.Header>
            <Card.Body>
              <Form.Group className="mb-3">
                <Form.Control 
                  type="file" 
                  onChange={(e: any) => setUploadFile(e.target.files[0])} 
                />
              </Form.Group>
              <Button variant="primary" onClick={handleUpload} disabled={!uploadFile}>
                Upload Excel
              </Button>
            </Card.Body>
          </Card>

          <Card>
            <Card.Header>Source Files</Card.Header>
            <ListGroup variant="flush">
              {sourceFiles.map(f => (
                <ListGroup.Item 
                  key={f.id} 
                  action 
                  active={selectedFile === f.id}
                  onClick={() => viewFileData(f.id)}
                >
                  {f.filename}
                  <div className="small text-muted">{new Date(f.uploaded_at).toLocaleString()}</div>
                </ListGroup.Item>
              ))}
            </ListGroup>
          </Card>
        </Col>

        <Col md={8}>
          <Card>
            <Card.Header>
              Data Explorer {selectedFile && <Badge bg="info">File ID: {selectedFile}</Badge>}
            </Card.Header>
            <Card.Body style={{ overflowX: 'auto' }}>
              {selectedFile ? (
                <Table striped bordered hover size="sm">
                  <thead>
                    <tr>
                      <th>Row</th>
                      {columns.map(col => <th key={col}>{col}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {Object.keys(rows).map(rowIdx => (
                      <tr key={rowIdx}>
                        <td>{rowIdx}</td>
                        {columns.map(col => (
                          <td key={col}>{rows[rowIdx][col]}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </Table>
              ) : (
                <div className="text-center py-5 text-muted">Select a file to explore data</div>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  )
}

export default App