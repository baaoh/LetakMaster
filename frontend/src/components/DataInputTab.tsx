import { useState, useEffect } from 'react'
import { Card, Button, Form, ListGroup, Row, Col, Alert, Spinner, Badge, InputGroup } from 'react-bootstrap'
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
  const [showSidebar, setShowSidebar] = useState(true)
  const [availableSheets, setAvailableSheets] = useState<string[]>([])

  useEffect(() => {
    fetchConfig()
    fetchHistory()
  }, [])

  // Auto-list sheets when config loads if path exists
  useEffect(() => {
      if (config.master_excel_path) {
          // Don't auto-call too aggressively, maybe just once or when user asks
          // But if we have a path, we want to populate the dropdown.
          // handleListSheets() 
          // Better: Only call if availableSheets is empty?
      }
  }, [config.master_excel_path])

  const fetchConfig = async () => {
    try {
      const resp = await axios.get(`${API_BASE}/config`)
      setConfig(resp.data)
      if (resp.data.master_excel_path) {
          // Try to load sheets immediately
          handleListSheets(resp.data.master_excel_path, resp.data.excel_password)
      }
    } catch (err) {
      console.error(err)
    }
  }

  const fetchHistory = async () => {
    try {
      const resp = await axios.get(`${API_BASE}/history`)
      setHistory(resp.data)
      if (resp.data.length > 0 && !selectedStateId) {
        loadState(resp.data[0].id)
      }
    } catch (err) {
      console.error(err)
    }
  }

  const loadState = async (id: number) => {
    setSelectedStateId(id)
    try {
      const resp = await axios.get(`${API_BASE}/state/${id}/data?t=${new Date().getTime()}`)
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
        if (resp.data.new_state_id) loadState(resp.data.new_state_id)
      } else {
        setMsg({ type: 'success', text: 'No changes detected. Loaded latest state.' })
        if (resp.data.latest_id && selectedStateId !== resp.data.latest_id) {
            loadState(resp.data.latest_id)
        }
      }
    } catch (err: any) {
      setMsg({ type: 'danger', text: err.response?.data?.detail || 'Sync failed.' })
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation() // Prevent row selection
    const password = window.prompt("Enter Admin/Excel Password to delete:")
    if (!password) return

    try {
      await axios.delete(`${API_BASE}/state/${id}`, { params: { password } })
      fetchHistory()
      if (selectedStateId === id) {
        setSelectedStateId(null)
        setStateData([])
      }
    } catch (err) {
      alert("Failed to delete. Incorrect password?")
    }
  }

  const handleOpenExcel = async () => {
    try {
        await axios.post(`${API_BASE}/open-excel`)
    } catch (err) {
        alert("Failed to open Excel. Is the path correct?")
    }
  }

  const handleBrowse = async () => {
    try {
        const resp = await axios.post(`${API_BASE}/system/browse-file`)
        if (resp.data.path) {
            setConfig(prev => ({ ...prev, master_excel_path: resp.data.path }))
            // Auto-load sheets
            handleListSheets(resp.data.path, config.excel_password)
        }
    } catch (err) {
        console.error(err)
    }
  }

  const handleListSheets = async (path?: string | null, password?: string | null) => {
      const p = path || config.master_excel_path
      const pw = password || config.excel_password
      if (!p) return
      
      try {
          const resp = await axios.post(`${API_BASE}/excel/sheets`, { path: p, password: pw })
          setAvailableSheets(resp.data)
      } catch (err) {
          console.error("Failed to list sheets")
          // Silent fail or toast? Silent for now to avoid spam on load
      }
  }

  const groupedHistory = history.reduce((acc, state) => {
    const key = `${state.source_path || 'Unknown'}::${state.source_sheet || 'Default'}`
    if (!acc[key]) acc[key] = []
    acc[key].push(state)
    return acc
  }, {} as Record<string, ProjectState[]>)

  const toggleGroup = (key: string) => {
    setExpandedGroups(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const getFilename = (path: string) => path.replace(/\\/g, '/').split('/').pop()

  return (
    <div className="d-flex" style={{ height: 'calc(100vh - 150px)', border: '1px solid #dee2e6' }}>
      {/* Sidebar */}
      {showSidebar && (
        <div style={{ width: '500px', minWidth: '500px', overflowY: 'auto' }} className="border-end bg-light p-3">
            <Card className="mb-4 shadow-sm">
            <Card.Header>Source Configuration</Card.Header>
            <Card.Body>
                <Form>
                <Form.Group className="mb-3">
                    <Form.Label>Master Excel Path</Form.Label>
                    <InputGroup>
                        <Form.Control 
                        type="text" 
                        value={config.master_excel_path || ''} 
                        onChange={e => setConfig({ ...config, master_excel_path: e.target.value })}
                        placeholder="C:/path/to/file.xls"
                        />
                        <Button variant="secondary" onClick={handleBrowse}>Browse...</Button>
                    </InputGroup>
                </Form.Group>
                
                <Form.Group className="mb-3">
                    <Form.Label>Excel Password (Optional)</Form.Label>
                    <Form.Control 
                    type="password" 
                    value={config.excel_password || ''} 
                    onChange={e => {
                        setConfig({ ...config, excel_password: e.target.value })
                        // If user types password, maybe we should reload sheets?
                        // But typing triggers many renders. Add a button instead.
                    }}
                    placeholder="Enter password if protected"
                    />
                </Form.Group>

                <Form.Group className="mb-3">
                    <Form.Label>Watched Sheet Name</Form.Label>
                    <InputGroup>
                        <Form.Select 
                            value={config.watched_sheet_name || ''}
                            onChange={e => setConfig({ ...config, watched_sheet_name: e.target.value })}
                        >
                            <option value="">-- Select Sheet --</option>
                            {availableSheets.map(s => <option key={s} value={s}>{s}</option>)}
                            {/* Keep current value even if not in list (legacy) */}
                            {config.watched_sheet_name && !availableSheets.includes(config.watched_sheet_name) && (
                                <option value={config.watched_sheet_name}>{config.watched_sheet_name}</option>
                            )}
                        </Form.Select>
                        <Button variant="outline-secondary" onClick={() => handleListSheets()}>
                            ⟳
                        </Button>
                    </InputGroup>
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

            <Card className="shadow-sm">
            <Card.Header>State History</Card.Header>
            <ListGroup variant="flush">
                {Object.keys(groupedHistory).map(groupKey => {
                const [path, sheet] = groupKey.split('::')
                const states = groupedHistory[groupKey]
                const isExpanded = expandedGroups[groupKey]
                const visibleStates = isExpanded ? states : states.slice(0, 5)
                
                return (
                    <div key={groupKey} className="border-bottom">
                    <div className="p-2 bg-light text-muted small fw-bold text-truncate" title={`${path} (${sheet})`}>
                        {getFilename(path)} - {sheet}
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
        </div>
      )}

      {/* Main Content */}
      <div className="flex-grow-1 d-flex flex-column p-3 bg-white">
        <div className="d-flex justify-content-between mb-3 align-items-center">
            <div className="d-flex align-items-center gap-3">
                <Button variant="outline-secondary" onClick={() => setShowSidebar(!showSidebar)}>
                    {showSidebar ? 'Hide Sidebar' : 'Show Sidebar'}
                </Button>
                {config.watched_sheet_name && (
                    <h4 className="m-0 text-primary">
                        Sheet: <strong>{config.watched_sheet_name}</strong>
                    </h4>
                )}
            </div>
            
            <div className="d-flex align-items-center gap-2">
                {selectedStateId && <span className="text-muted small">State #{selectedStateId}</span>}
                <Button variant="primary" onClick={handleOpenExcel}>
                    Open Master Excel
                </Button>
            </div>
        </div>
        
        <div className="flex-grow-1 border rounded" style={{ overflow: 'hidden', position: 'relative' }}>
            <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, overflow: 'auto' }}>
                <DataGrid data={stateData} />
            </div>
        </div>
      </div>
    </div>
  )
}