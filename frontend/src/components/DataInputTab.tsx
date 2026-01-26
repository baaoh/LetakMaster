import { useState, useEffect, useMemo } from 'react'
import { Card, Button, Form, ListGroup, Row, Col, Alert, Spinner, Badge, InputGroup, ProgressBar } from 'react-bootstrap'
import axios from 'axios'
import { DataGrid } from './DataGrid'

const API_BASE = 'http://localhost:8000'

interface AppConfig {
  master_excel_path: string | null
  watched_sheet_name: string | null
  excel_password: string | null
  images_path: string | null
  build_json_path: string | null
}

interface ProjectState {
  id: number
  created_at: string
  created_by: string
  excel_hash: string
  source_path: string | null
  source_sheet: string | null
  excel_last_modified_by: string | null
  local_version?: number
}

interface AutomationReport {
    status: string
    details?: string
    pages?: number[]
    count?: number
    error?: string
    output_path?: string
}

export function DataInputTab() {
  const [config, setConfig] = useState<AppConfig>({ 
      master_excel_path: '', watched_sheet_name: '', excel_password: '', images_path: '', build_json_path: '' 
  })
  const [history, setHistory] = useState<ProjectState[]>([])
  const [selectedStateId, setSelectedStateId] = useState<number | null>(null)
  const [stateData, setStateData] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [syncStatus, setSyncStatus] = useState<string | null>(null)
  const [msg, setMsg] = useState<{ type: 'success' | 'danger', text: string } | null>(null)
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>({})
  const [showSidebar, setShowSidebar] = useState(true)
  const [availableSheets, setAvailableSheets] = useState<string[]>([])
  
  // Automation State
  const [workspacePath, setWorkspacePath] = useState<string | null>(null)
  const [enrichResult, setEnrichResult] = useState<AutomationReport | null>(null)
  const [genResult, setGenResult] = useState<AutomationReport | null>(null)

  // Initial Load
  useEffect(() => {
    const init = async () => {
        setLoading(true)
        await Promise.all([fetchConfig(), fetchHistory()])
        setLoading(false)
    }
    init()
  }, [])

  const fetchConfig = async () => {
    try {
      const resp = await axios.get(`${API_BASE}/config`)
      setConfig(resp.data)
      if (resp.data.master_excel_path) {
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
      setStateData([])
    }
  }

  const handleSync = async () => {
    setLoading(true)
    setMsg(null)
    setSyncStatus("Initializing Sync...")
    
    try {
      const response = await fetch(`${API_BASE}/sync`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(config)
      })
      
      const reader = response.body?.getReader()
      if (!reader) throw new Error("No response stream")
      
      const decoder = new TextDecoder()
      let buffer = ''
      
      while (true) {
          const { done, value } = await reader.read()
          if (done) break
          
          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          buffer = lines.pop() || '' 
          
          for (const line of lines) {
              if (!line.trim()) continue
              try {
                  const update = JSON.parse(line)
                  if (update.status === 'progress') {
                      setSyncStatus(update.message)
                  } else if (update.status === 'error') {
                      setMsg({ type: 'danger', text: update.message })
                  } else if (update.status === 'done') {
                      setSyncStatus(null)
                      if (update.result === 'updated') {
                          setMsg({ type: 'success', text: 'New state recorded!' })
                          await fetchHistory()
                          if (update.new_state_id) loadState(update.new_state_id)
                      } else {
                          setMsg({ type: 'success', text: 'No changes detected. Loaded latest state.' })
                          if (update.latest_id) loadState(update.latest_id)
                      }
                  }
              } catch (e) {
                  console.error("JSON Parse error", e)
              }
          }
      }
    } catch (err: any) {
      setMsg({ type: 'danger', text: err.message || 'Sync failed.' })
    } finally {
      setLoading(false)
      setSyncStatus(null)
    }
  }

  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation()
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
        if (selectedStateId) {
            setLoading(true)
            const resp = await axios.post(`${API_BASE}/state/${selectedStateId}/open`)
            setLoading(false)
            if (resp.data.status === 'cancelled') return 

            setWorkspacePath(resp.data.path)
            setEnrichResult(null)
            setGenResult(null)
        } else {
            await axios.post(`${API_BASE}/open-excel`)
        }
    } catch (err) {
        setLoading(false)
        alert("Failed to open Excel.")
    }
  }

  const handleEnrich = async () => {
      setLoading(true)
      try {
          const resp = await axios.post(`${API_BASE}/system/automation/enrich`, config)
          setEnrichResult(resp.data.report)
      } catch (e: any) {
          alert("Enrichment failed: " + (e.response?.data?.detail || e.message))
      } finally {
          setLoading(false)
      }
  }

  const handleGenerate = async () => {
      setLoading(true)
      try {
          const resp = await axios.post(`${API_BASE}/system/automation/generate`, config)
          setGenResult(resp.data.report)
      } catch (e: any) {
          alert("Generation failed: " + (e.response?.data?.detail || e.message))
      } finally {
          setLoading(false)
      }
  }

  const handleOpenPhotoshop = async () => {
      try {
          await axios.post(`${API_BASE}/system/open-photoshop`)
      } catch (e: any) {
          alert("Failed to launch Photoshop: " + (e.response?.data?.detail || e.message))
      }
  }

  const handleRunBuilder = async () => {
      try {
          // Pass the selected state ID so the backend can prioritize its paths
          const url = selectedStateId 
            ? `${API_BASE}/system/run-builder-script?state_id=${selectedStateId}`
            : `${API_BASE}/system/run-builder-script`
            
          await axios.post(url)
      } catch (e: any) {
          alert("Failed to run script: " + (e.response?.data?.detail || e.message))
      }
  }

  const handleBrowse = async () => {
    try {
        const resp = await axios.post(`${API_BASE}/system/browse-file`)
        if (resp.data.path) {
            setConfig(prev => ({ ...prev, master_excel_path: resp.data.path }))
            handleListSheets(resp.data.path, config.excel_password)
        }
    } catch (err) {
        console.error(err)
    }
  }

          const handleBrowseFolder = async (field: 'images_path' | 'build_json_path') => {
              try {
                  const resp = await axios.post(`${API_BASE}/system/browse-folder`)
                  if (resp.data.path) {
                      const newPath = resp.data.path
                      const newConfig = { ...config, [field]: newPath }
                      
                      setConfig(newConfig)
                      // Auto-save to persist immediately
                      await axios.post(`${API_BASE}/config`, newConfig)
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
      }
  }

  const toggleGroup = (key: string) => {
    setExpandedGroups(prev => ({ ...prev, [key]: !prev[key] }))
  }

  const getFilename = (path: string) => {
      return path.split('\\').join('/').split('/').pop() || 'Unknown'
  }

  // Process History for Display (Grouping + Local Versioning)
  const groupedHistory = useMemo(() => {
      const groups: Record<string, ProjectState[]> = {}
      
      history.forEach(state => {
          const key = `${state.source_path || 'Unknown'}::${state.source_sheet || 'Default'}`
          if (!groups[key]) groups[key] = []
          groups[key].push(state)
      })

      Object.keys(groups).forEach(key => {
          const sorted = [...groups[key]].sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
          sorted.forEach((state, idx) => {
              state.local_version = idx + 1
          })
          groups[key] = sorted.reverse()
      })
      
      return groups
  }, [history])

  // Derive title from selected state
  const selectedState = history.find(s => s.id === selectedStateId)
  const displaySheetName = selectedState ? selectedState.source_sheet : config.watched_sheet_name

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
                    <Form.Label>Excel Password</Form.Label>
                    <Form.Control 
                    type="password" 
                    value={config.excel_password || ''} 
                    onChange={e => setConfig({ ...config, excel_password: e.target.value })}
                    placeholder="Optional"
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
                            {config.watched_sheet_name && !availableSheets.includes(config.watched_sheet_name) && (
                                <option value={config.watched_sheet_name}>{config.watched_sheet_name}</option>
                            )}
                        </Form.Select>
                        <Button variant="outline-secondary" onClick={() => handleListSheets()}>
                            ⟳
                        </Button>
                    </InputGroup>
                </Form.Group>

                <hr/>
                <h6 className="text-muted">Automation Paths</h6>
                
                <Form.Group className="mb-2">
                    <Form.Label className="small">Images Directory</Form.Label>
                    <InputGroup size="sm">
                        <Form.Control 
                        type="text" 
                        value={config.images_path || ''} 
                        onChange={e => setConfig({ ...config, images_path: e.target.value })}
                        placeholder="Folder containing product images"
                        />
                        <Button variant="secondary" onClick={() => handleBrowseFolder('images_path')}>...</Button>
                    </InputGroup>
                </Form.Group>

                <Form.Group className="mb-3">
                    <Form.Label className="small">Build Plans Directory</Form.Label>
                    <InputGroup size="sm">
                        <Form.Control 
                        type="text" 
                        value={config.build_json_path || ''} 
                        onChange={e => setConfig({ ...config, build_json_path: e.target.value })}
                        placeholder="Default: workspaces/build_plans"
                        />
                        <Button variant="secondary" onClick={() => handleBrowseFolder('build_json_path')}>...</Button>
                    </InputGroup>
                </Form.Group>

                <div className="d-grid gap-2">
                    <Button variant="success" onClick={handleSync} disabled={loading}>
                    {loading && !syncStatus ? <Spinner size="sm" animation="border" /> : 'Sync Now'}
                    </Button>
                    {syncStatus && (
                        <div className="mt-2">
                            <ProgressBar animated now={100} label={syncStatus} style={{height: '25px', fontSize: '0.8rem'}} />
                        </div>
                    )}
                </div>
                </Form>
                {msg && <Alert variant={msg.type} className="mt-3 small">{msg.text}</Alert>}
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
                            <strong>v{state.local_version}</strong> <span className="small text-muted">{new Date(state.created_at).toLocaleString()}</span>
                            {state.excel_last_modified_by && (
                                <div className="small text-primary">Last: {state.excel_last_modified_by}</div>
                            )}
                            </div>
                            <div className="d-flex align-items-center gap-2">
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
                {history.length === 0 && <div className="p-3 text-muted">No history yet.</div>}
            </ListGroup>
            </Card>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-grow-1 d-flex flex-column p-3 bg-white">
        <div className="d-flex justify-content-between mb-3 align-items-center">
            <div className="d-flex align-items-center gap-3">
                <Button variant="outline-secondary" onClick={() => setShowSidebar(!showSidebar)}>
                    {showSidebar ? 'Hide' : 'Show'}
                </Button>
                {displaySheetName && (
                    <h4 className="m-0 text-primary">
                        Sheet: <strong>{displaySheetName}</strong>
                    </h4>
                )}
            </div>
            
            <div className="d-flex align-items-center gap-2">
                {selectedStateId && (
                    <span className="text-muted small">
                        v{history.find(s => s.id === selectedStateId)?.local_version} 
                        (Global #{selectedStateId})
                    </span>
                )}
                <Button variant="primary" onClick={handleOpenExcel} disabled={loading}>
                    {loading ? <Spinner size="sm" animation="border"/> : (selectedStateId ? 'Open Workspace (Copy)' : 'Open Master Excel')}
                </Button>
            </div>
        </div>
        
        {/* Automation Panel */}
        {workspacePath && (
            <Alert variant="info" onClose={() => { setWorkspacePath(null); setEnrichResult(null); setGenResult(null); }} dismissible className="mb-3">
                <Alert.Heading>Workspace Active</Alert.Heading>
                
                <p className="mb-2">
                    Attached to: <strong>{getFilename(workspacePath)}</strong>
                </p>
                
                <Row className="align-items-center">
                    <Col md={3}>
                        <Button variant="warning" onClick={handleEnrich} disabled={loading} className="w-100">
                            1. Calculate Layouts
                        </Button>
                    </Col>
                    <Col md={3}>
                        <Button variant="success" onClick={handleGenerate} disabled={loading} className="w-100">
                            2. Export Build Plans
                        </Button>
                    </Col>
                    <Col md={6}>
                        {/* Results Display */}
                        {enrichResult && (
                            <div className="mb-1">
                                <Badge bg={enrichResult.status === 'success' ? 'success' : 'danger'}>Enrichment</Badge>
                                <span className="ms-2 small text-muted">{enrichResult.details}</span>
                            </div>
                        )}
                        {genResult && (
                            <div>
                                <Badge bg={genResult.status === 'success' ? 'success' : 'danger'}>Export</Badge>
                                {genResult.status === 'success' ? (
                                    <span className="ms-2 small">
                                        Saved to: <strong>{genResult.output_path?.split('workspaces')[1] || genResult.output_path}</strong>
                                    </span>
                                ) : (
                                    <span className="ms-2 small text-danger">{genResult.error}</span>
                                )}
                            </div>
                        )}
                    </Col>
                </Row>
                
                {(genResult && genResult.status === 'success') && (
                    <>
                        <hr />
                        <div className="d-flex gap-2 justify-content-end">
                            <Button variant="outline-dark" size="sm" onClick={handleOpenPhotoshop}>
                                3. Launch Photoshop
                            </Button>
                            <Button variant="dark" size="sm" onClick={handleRunBuilder}>
                                4. Run Builder Script
                            </Button>
                        </div>
                    </>
                )}
            </Alert>
        )}
        
        <div className="flex-grow-1 border rounded" style={{ overflow: 'hidden', position: 'relative' }}>
            <div style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, overflow: 'auto' }}>
                <DataGrid data={stateData} />
            </div>
        </div>
      </div>
    </div>
  )
}