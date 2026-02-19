import { useState, useEffect } from 'react'
import { Card, Button, ListGroup, Row, Col, Badge, Table, Spinner, Modal, Form, InputGroup, Tabs, Tab, Accordion, Alert } from 'react-bootstrap'
import axios from 'axios'
import { DataGrid } from './DataGrid'

const HUB_URL = import.meta.env.VITE_HUB_URL || 'http://localhost:8000'
const AGENT_URL = import.meta.env.VITE_AGENT_URL || 'http://localhost:8001'

interface State {
    id: number
    created_at: string
    created_by: string
    sheet_name: string
    excel_author: string
    summary: string
    archive_path: string
    parent_id: number | null
}

interface Diff {
    page: number
    product: string
    field: string
    old: string | null
    new: string | null
    type: string
}

export function CollaborationTab() {
    const [history, setHistory] = useState<State[]>([])
    const [loading, setLoading] = useState(false)
    const [fetchingDetails, setFetchingDetails] = useState(false)
    const [selectedState, setSelectedState] = useState<State | null>(null)
    const [diffs, setDiffs] = useState<Diff[]>([])
    const [inspectData, setInspectData] = useState<any[]>([])
    const [activeViewTab, setActiveViewTab] = useState('diffs')
    
    const [showSyncModal, setShowSyncModal] = useState(false)
    const [syncConfig, setSyncConfig] = useState({ 
        excel_path: localStorage.getItem('last_excel_path') || '', 
        images_path: localStorage.getItem('last_images_path') || 'K:/LetakMaster_Assets/Product_Photos',
        sheet_name: '', 
        password: localStorage.getItem('last_excel_password') || '' 
    })
    const [availableSheets, setAvailableSheets] = useState<string[]>([])
    const [fetchingSheets, setFetchingSheets] = useState(false)

    const [designing, setDesigning] = useState(false)
    const [localExcelOpen, setLocalExcelOpen] = useState(false)
    const [psConnected, setPsConnected] = useState(false)

    const PROJECT_ID = 1

    useEffect(() => {
        fetchHistory()
    }, [])

    const fetchHistory = async () => {
        setLoading(true)
        try {
            const resp = await axios.get(`${HUB_URL}/sync/history/${PROJECT_ID}`)
            if (Array.isArray(resp.data)) setHistory(resp.data)
        } catch (e) { console.error("Hub connection failed") }
        finally { setLoading(false) }
    }

    const loadStateDetails = async (state: State) => {
        setSelectedState(state)
        setFetchingDetails(true)
        try {
            const [diffResp, snapResp] = await Promise.all([
                axios.get(`${HUB_URL}/sync/diff/${state.id}`),
                axios.get(`${HUB_URL}/sync/snapshot/${state.id}`)
            ])
            setDiffs(Array.isArray(diffResp.data) ? diffResp.data : [])
            setInspectData(Array.isArray(snapResp.data) ? snapResp.data : [])
        } catch (e) { console.error("Failed to load details") }
        finally { setFetchingDetails(false) }
    }

    const handleDesignerAction = async (action: string) => {
        setDesigning(true)
        try {
            let payload: any = {
                excel_path: syncConfig.excel_path,
                sheet_name: syncConfig.sheet_name,
                password: syncConfig.password
            };

            if (action === 'open-excel' && selectedState) {
                payload.excel_path = selectedState.archive_path;
                payload.sheet_name = selectedState.sheet_name;
            }

            if (action === 'run-builder') {
                payload = { images_path: syncConfig.images_path };
            }

            const resp = await axios.post(`${AGENT_URL}/automation/${action}`, payload)
            
            if (action === 'open-excel' && resp.data.status === 'success') {
                setLocalExcelOpen(true)
                localStorage.setItem('last_excel_path', payload.excel_path)
                if (payload.password) localStorage.setItem('last_excel_password', payload.password)
            }
            if (action === 'launch-ps' && resp.data.status === 'success') {
                setPsConnected(true)
            }
            alert(resp.data.message || "Action Completed")
        } catch (e: any) { 
            alert("Error: " + (e.response?.data?.detail || e.message))
        } finally { 
            setDesigning(false) 
        }
    }

    const handleDelete = async (id: number) => {
        if (!window.confirm(`Delete State #${id}?`)) return
        try {
            await axios.delete(`${HUB_URL}/sync/state/${id}`)
            if (selectedState?.id === id) setSelectedState(null)
            fetchHistory()
        } catch (e) { alert("Delete failed.") }
    }

    const runSync = async () => {
        if (!syncConfig.sheet_name) return alert("Please select a sheet.")
        setLoading(true)
        try {
            await axios.post(`${AGENT_URL}/automation/sync-excel`, { project_id: PROJECT_ID, ...syncConfig })
            localStorage.setItem('last_excel_password', syncConfig.password)
            setShowSyncModal(false)
            fetchHistory()
        } catch (e: any) { alert("Sync Failed: " + (e.response?.data?.detail || e.message)) }
        finally { setLoading(false) }
    }

    const groupedHistory: { [key: string]: State[] } = (Array.isArray(history) ? history : []).reduce((acc: any, state) => {
        const key = state.sheet_name || "Unknown Week"
        if (!acc[key]) acc[key] = []
        acc[key].push(state)
        return acc
    }, {})

    return (
        <Row className="g-3">
            <Col md={3}>
                <Card className="shadow-sm border-primary border-2 mb-3">
                    <Card.Header className="bg-primary text-white d-flex justify-content-between align-items-center">
                        <strong style={{fontSize: '0.85rem'}}>🎨 Designer Controls</strong>
                        {designing && <Spinner size="sm" animation="border" variant="light" />}
                    </Card.Header>
                    <Card.Body className="p-2">
                        <div className="d-grid gap-2 text-center">
                            {/* 1. EXCEL BUTTON */}
                            <Button variant={localExcelOpen ? "success" : "primary"} size="sm" className="fw-bold" onClick={() => handleDesignerAction('open-excel')}>
                                {localExcelOpen ? "✅ Excel Active" : (selectedState ? `1. Open State #${selectedState.id}` : "1. Open Local File")}
                            </Button>
                            
                            {/* 2. PHOTOSHOP BUTTON */}
                            <Button variant={psConnected ? "success" : "outline-info"} size="sm" className="fw-bold" onClick={() => handleDesignerAction('launch-ps')}>
                                {psConnected ? "✅ Photoshop Linked" : "2. Connect Photoshop"}
                            </Button>

                            <Button variant="outline-secondary" size="sm" onClick={() => setShowSyncModal(true)}>
                                <i className="bi bi-gear me-1"></i> Configure / Sync...
                            </Button>

                            <hr className="my-1"/>
                            <Button variant="outline-dark" size="sm" onClick={() => handleDesignerAction('calculate-layouts')} disabled={!localExcelOpen}>3. Calculate Layouts</Button>
                            <Button variant="outline-dark" size="sm" onClick={() => handleDesignerAction('export-plans')} disabled={!localExcelOpen}>4. Export Build Plans</Button>
                            <Button variant="dark" size="sm" onClick={() => handleDesignerAction('run-builder')} disabled={!localExcelOpen || !psConnected}>5. Run PS Builder</Button>
                        </div>
                    </Card.Body>
                </Card>

                <Card className="shadow-sm border-0 bg-white" style={{ height: 'calc(100vh - 520px)', overflowY: 'auto' }}>
                    <Card.Header className="bg-dark text-white sticky-top d-flex justify-content-between align-items-center py-1">
                        <strong style={{fontSize: '0.8rem'}}>🌍 Timeline</strong>
                        <Button variant="link" className="text-white p-0" onClick={fetchHistory}>⟳</Button>
                    </Card.Header>
                    <div className="d-grid p-2 border-bottom">
                        <Button variant="success" size="sm" onClick={() => setShowSyncModal(true)}>+ Publish Sync</Button>
                    </div>
                    <Accordion flush>
                        {Object.keys(groupedHistory).map((sheet, index) => (
                            <Accordion.Item eventKey={index.toString()} key={sheet}>
                                <Accordion.Header><span className="fw-bold text-primary small">{sheet}</span></Accordion.Header>
                                <Accordion.Body className="p-0">
                                    <ListGroup variant="flush">
                                        {groupedHistory[sheet].map(state => (
                                            <ListGroup.Item key={state.id} action active={selectedState?.id === state.id} onClick={() => loadStateDetails(state)} className="py-1">
                                                <div className="d-flex justify-content-between align-items-center">
                                                    <div style={{fontSize: '0.7rem'}}>
                                                        <strong>#{state.id}</strong> <span className="text-muted">{new Date(state.created_at).toLocaleTimeString()}</span>
                                                        <div className="text-primary fw-bold">👤 {state.excel_author}</div>
                                                    </div>
                                                    <Button variant="link" className="text-danger p-0" onClick={(e) => { e.stopPropagation(); handleDelete(state.id); }}>×</Button>
                                                </div>
                                            </ListGroup.Item>
                                        ))}
                                    </ListGroup>
                                </Accordion.Body>
                            </Accordion.Item>
                        ))}
                    </Accordion>
                </Card>
            </Col>

            <Col md={9}>
                {selectedState ? (
                    <Card className="shadow-sm border-0" style={{ height: 'calc(100vh - 180px)' }}>
                        <Card.Header className="bg-dark text-white d-flex justify-content-between align-items-center py-1">
                            <div><strong>Week: {selectedState.sheet_name}</strong> <Badge bg="primary">State #{selectedState.id}</Badge></div>
                            <div className="small text-info">By {selectedState.created_by}</div>
                        </Card.Header>
                        <Card.Body className="p-0 d-flex flex-column bg-white">
                            <Tabs activeKey={activeViewTab} onSelect={(k) => setActiveViewTab(k || 'diffs')} className="bg-light px-2 pt-2 border-bottom">
                                <Tab eventKey="diffs" title={`📂 Changes (${diffs.length})`}>
                                    <div className="p-3" style={{ overflowY: 'auto', maxHeight: 'calc(100vh - 280px)' }}>
                                        {fetchingDetails ? <div className="text-center p-5"><Spinner animation="border"/> Loading...</div> : <DiffTable diffs={diffs} />}
                                    </div>
                                </Tab>
                                <Tab eventKey="inspect" title="🔍 Full Snapshot">
                                    <div style={{ height: 'calc(100vh - 280px)' }}>
                                        {fetchingDetails ? <div className="text-center p-5"><Spinner animation="border"/> Loading...</div> : <DataGrid data={inspectData} />}
                                    </div>
                                </Tab>
                            </Tabs>
                        </Card.Body>
                    </Card>
                ) : (
                    <div className="h-100 d-flex flex-column align-items-center justify-content-center text-muted border rounded bg-light border-dashed">
                        <i className="bi bi-cloud-check mb-3" style={{fontSize: '3rem'}}></i>
                        <h4>LetakMaster Collaborative Suite</h4>
                        <p>Configure your workspace or select a history state to begin.</p>
                    </div>
                )}
            </Col>

            <Modal show={showSyncModal} onHide={() => setShowSyncModal(false)}>
                <Modal.Header closeButton><Modal.Title>Workspace Configuration</Modal.Title></Modal.Header>
                <Modal.Body>
                    <Form>
                        <Form.Group className="mb-3">
                            <Form.Label>Excel File</Form.Label>
                            <InputGroup>
                                <Form.Control value={syncConfig.excel_path} readOnly placeholder="Browse..."/>
                                <Button variant="secondary" onClick={async () => {
                                    const r = await axios.post(`${AGENT_URL}/automation/browse-file`);
                                    if (r.data.path) {
                                        setSyncConfig({...syncConfig, excel_path: r.data.path});
                                        localStorage.setItem('last_excel_path', r.data.path);
                                    }
                                }}>Browse</Button>
                            </InputGroup>
                        </Form.Group>
                        
                        <Form.Group className="mb-3">
                            <Form.Label>Product Photos Folder</Form.Label>
                            <InputGroup>
                                <Form.Control 
                                    value={syncConfig.images_path} 
                                    onChange={e => {
                                        setSyncConfig({...syncConfig, images_path: e.target.value});
                                        localStorage.setItem('last_images_path', e.target.value);
                                    }}
                                    placeholder="K:/Path/To/Photos"
                                />
                            </InputGroup>
                            <Form.Text className="text-muted">Folder where Photoshop should look for product images.</Form.Text>
                        </Form.Group>

                        <Form.Group className="mb-3">
                            <Form.Label>Excel Password (if protected)</Form.Label>
                            <Form.Control 
                                type="password" 
                                value={syncConfig.password} 
                                onChange={e => setSyncConfig({...syncConfig, password: e.target.value})}
                                placeholder="Enter password to unlock file"
                            />
                        </Form.Group>
                        <hr/>
                        <div className="small fw-bold text-muted mb-2">Sheet Selection (For Syncing)</div>
                        <Form.Group className="mb-3">
                            <InputGroup>
                                <Form.Select value={syncConfig.sheet_name} onChange={e => setSyncConfig({...syncConfig, sheet_name: e.target.value})}>
                                    <option value="">-- Choose Sheet --</option>
                                    {availableSheets.map(s => <option key={s} value={s}>{s}</option>)}
                                </Form.Select>
                                <Button onClick={async () => {
                                    setFetchingSheets(true)
                                    try {
                                        const r = await axios.post(`${AGENT_URL}/automation/sheets`, { excel_path: syncConfig.excel_path, password: syncConfig.password })
                                        setAvailableSheets(r.data)
                                        if (r.data.length > 0) setSyncConfig(p => ({ ...p, sheet_name: r.data[0] }))
                                    } finally { setFetchingSheets(false) }
                                }}>Refresh List</Button>
                            </InputGroup>
                        </Form.Group>
                    </Form>
                </Modal.Body>
                <Modal.Footer>
                    <Button variant="primary" onClick={() => {
                        localStorage.setItem('last_excel_path', syncConfig.excel_path);
                        localStorage.setItem('last_excel_password', syncConfig.password);
                        setShowSyncModal(false);
                    }}>Save Config</Button>
                    <Button variant="success" onClick={runSync} disabled={!syncConfig.sheet_name || loading}>Publish My Work (Sync)</Button>
                </Modal.Footer>
            </Modal>
        </Row>
    )
}

function DiffTable({ diffs }: { diffs: Diff[] }) {
    if (diffs.length === 0) return <div className="p-4 text-center text-muted">No specific field changes.</div>
    return (
        <Table size="sm" hover className="small border shadow-sm">
            <thead className="table-light"><tr><th>Pg</th><th>Product</th><th>Field</th><th>Old</th><th>New</th></tr></thead>
            <tbody>
                {diffs.map((d, i) => (
                    <tr key={i}><td className="text-center"><Badge bg="secondary">{d.page}</Badge></td><td className="fw-bold">{d.product}</td><td>{d.field}</td><td className="text-danger text-decoration-line-through">{d.old}</td><td className="text-success fw-bold">{d.new}</td></tr>
                ))}
            </tbody>
        </Table>
    )
}
