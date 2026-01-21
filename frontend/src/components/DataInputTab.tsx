import { useState, useEffect } from 'react'
import { Card, Button, Form, ListGroup, Row, Col, Alert, Spinner, Badge } from 'react-bootstrap'
import axios from 'axios'
import { DataGrid } from './DataGrid'

const API_BASE = 'http://localhost:8000'

interface AppConfig {
  master_excel_path: string | null
  watched_sheet_name: string | null
  excel_password: string | null
}

interface ProjectState {
  id: number
  created_at: string
  created_by: string
  excel_hash: string
  source_path: string | null
  source_sheet: string | null
  excel_last_modified_by: string | null
}

export function DataInputTab() {
  const [config, setConfig] = useState<AppConfig>({ master_excel_path: '', watched_sheet_name: '', excel_password: '' })
  const [history, setHistory] = useState<ProjectState[]>([])
  const [selectedStateId, setSelectedStateId] = useState<number | null>(null)
  const [stateData, setStateData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState<{ type: 'success' | 'danger', text: string } | null>(null)
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({})

  // ... (existing functions) ...

  // Grouping Logic
  const groupedHistory = history.reduce((acc, state) => {
    const key = `${state.source_path || 'Unknown'}::${state.source_sheet || 'Default'}`
    if (!acc[key]) acc[key] = []
    acc[key].push(state)
    return acc
  }, {} as Record<string, ProjectState[]>)

  const toggleGroup = (key: string) => {
    setExpandedGroups(prev => ({ ...prev, [key]: !prev[key] }))
  }

  return (
    <Row>
      <Col md={4}>
        <Card className="mb-4">
          {/* ... Config Form ... */}
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
              <Form.Group className="mb-3">
                <Form.Label>Excel Password (Optional)</Form.Label>
                <Form.Control 
                  type="password" 
                  value={config.excel_password || ''} 
                  onChange={e => setConfig({ ...config, excel_password: e.target.value })}
                  placeholder="Enter password if protected"
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
          <ListGroup variant="flush" style={{ maxHeight: '600px', overflowY: 'auto' }}>
            {Object.keys(groupedHistory).map(groupKey => {
              const [path, sheet] = groupKey.split('::')
              const states = groupedHistory[groupKey]
              const isExpanded = expandedGroups[groupKey]
              const visibleStates = isExpanded ? states : states.slice(0, 5)
              
              return (
                <div key={groupKey} className="border-bottom">
                  <div className="p-2 bg-light text-muted small fw-bold text-truncate" title={`${path} (${sheet})`}>
                    {path.split(/[/\]/).pop()} - {sheet}
                  </div>
                  {visibleStates.map(state => (
                    <ListGroup.Item 
                      key={state.id} 
                      action 
                      active={selectedStateId === state.id}
                      onClick={() => loadState(state.id)}
                      className="border-0 border-bottom"
                    >
                      <div className="d-flex justify-content-between align-items-start">
                        <div>
                          <strong>#{state.id}</strong> <span className="small text-muted">{new Date(state.created_at).toLocaleString()}</span>
                          {state.excel_last_modified_by && (
                            <div className="small text-primary">Last Edit: {state.excel_last_modified_by}</div>
                          )}
                        </div>
                        <div className="d-flex align-items-center gap-2">
                          <Badge bg="secondary">{state.excel_hash.substring(0, 5)}</Badge>
                          <Button size="sm" variant="danger" style={{padding: '0px 6px'}} onClick={(e) => handleDelete(e, state.id)}>×</Button>
                        </div>
                      </div>
                    </ListGroup.Item>
                  ))}
                  {states.length > 5 && (
                    <div className="text-center p-1">
                      <Button variant="link" size="sm" onClick={() => toggleGroup(groupKey)}>
                        {isExpanded ? 'Show Less' : `Show ${states.length - 5} More...`}
                      </Button>
                    </div>
                  )}
                </div>
              )
            })}
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
