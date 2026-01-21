import { useState, useEffect } from 'react'
import { Card, Button, Form, ListGroup, Row, Col, Alert, Spinner, Badge } from 'react-bootstrap'
import axios from 'axios'
import { DataGrid } from './DataGrid'

const API_BASE = 'http://localhost:8000'

interface AppConfig {
  master_excel_path: string | null
  watched_sheet_name: string | null
}

interface ProjectState {
  id: number
  created_at: string
  created_by: string
  excel_hash: string
}

export function DataInputTab() {
  const [config, setConfig] = useState<AppConfig>({ master_excel_path: '', watched_sheet_name: '' })
  const [history, setHistory] = useState<ProjectState[]>([])
  const [selectedStateId, setSelectedStateId] = useState<number | null>(null)
  const [stateData, setStateData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState<{ type: 'success' | 'danger', text: string } | null>(null)

  useEffect(() => {
    fetchConfig()
    fetchHistory()
  }, [])

  const fetchConfig = async () => {
    try {
      const resp = await axios.get(`${API_BASE}/config`)
      setConfig(resp.data)
    } catch (err) {
      console.error(err)
    }
  }

  const fetchHistory = async () => {
    try {
      const resp = await axios.get(`${API_BASE}/history`)
      setHistory(resp.data)
    } catch (err) {
      console.error(err)
    }
  }

  const loadState = async (id: number) => {
    setSelectedStateId(id)
    try {
      const resp = await axios.get(`${API_BASE}/state/${id}/data`)
      setStateData(resp.data)
    } catch (err) {
      console.error(err)
      setMsg({ type: 'danger', text: 'Failed to load state data.' })
    }
  }

  const handleSaveConfig = async () => {
    try {
      await axios.post(`${API_BASE}/config`, config)
      setMsg({ type: 'success', text: 'Configuration saved.' })
    } catch (err) {
      setMsg({ type: 'danger', text: 'Failed to save config.' })
    }
  }

  const handleSync = async () => {
    setLoading(true)
    setMsg(null)
    try {
      const resp = await axios.post(`${API_BASE}/sync`)
      if (resp.data.status === 'updated') {
        setMsg({ type: 'success', text: 'New state recorded!' })
        fetchHistory()
        // Auto-load new state
        if (resp.data.new_state_id) loadState(resp.data.new_state_id)
      } else {
        setMsg({ type: 'success', text: 'No changes detected.' })
      }
    } catch (err: any) {
      setMsg({ type: 'danger', text: err.response?.data?.detail || 'Sync failed.' })
    } finally {
      setLoading(false)
    }
  }

  return (
    <Row>
      <Col md={4}>
        <Card className="mb-4">
          <Card.Header>Source Configuration</Card.Header>
          <Card.Body>
            <Form>
              <Form.Group className="mb-3">
                <Form.Label>Master Excel Path</Form.Label>
                <Form.Control 
                  type="text" 
                  value={config.master_excel_path || ''} 
                  onChange={e => setConfig({ ...config, master_excel_path: e.target.value })}
                  placeholder="C:/Data/Master.xlsx"
                />
              </Form.Group>
              <Form.Group className="mb-3">
                <Form.Label>Watched Sheet Name</Form.Label>
                <Form.Control 
                  type="text" 
                  value={config.watched_sheet_name || ''} 
                  onChange={e => setConfig({ ...config, watched_sheet_name: e.target.value })}
                  placeholder="Sheet1"
                />
              </Form.Group>
              <div className="d-flex justify-content-between">
                <Button variant="outline-primary" onClick={handleSaveConfig}>Save Config</Button>
                <Button variant="success" onClick={handleSync} disabled={loading}>
                  {loading ? <Spinner size="sm" animation="border" /> : 'Sync Now'}
                </Button>
              </div>
            </Form>
            {msg && <Alert variant={msg.type} className="mt-3">{msg.text}</Alert>}
          </Card.Body>
        </Card>

        <Card>
          <Card.Header>State History</Card.Header>
          <ListGroup variant="flush" style={{ maxHeight: '400px', overflowY: 'auto' }}>
            {history.map(state => (
              <ListGroup.Item 
                key={state.id} 
                action 
                active={selectedStateId === state.id}
                onClick={() => loadState(state.id)}
              >
                <div className="d-flex justify-content-between align-items-center">
                  <div>
                    <strong>State #{state.id}</strong>
                    <div className="small text-muted">{new Date(state.created_at).toLocaleString()}</div>
                  </div>
                  <Badge bg="secondary">{state.excel_hash.substring(0, 7)}</Badge>
                </div>
              </ListGroup.Item>
            ))}
            {history.length === 0 && <div className="p-3 text-muted">No history yet. Sync to create a state.</div>}
          </ListGroup>
        </Card>
      </Col>
      
      <Col md={8}>
        <Card>
          <Card.Header>
            Data View {selectedStateId && <Badge bg="info">State #{selectedStateId}</Badge>}
          </Card.Header>
          <Card.Body className="p-0">
            <DataGrid data={stateData} />
          </Card.Body>
        </Card>
      </Col>
    </Row>
  )
}
