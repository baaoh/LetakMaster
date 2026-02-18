import { useState, useEffect } from 'react'
import { Card, Button, ListGroup, Row, Col, Badge, Table, Spinner, Modal, Form, InputGroup, Tabs, Tab, Accordion } from 'react-bootstrap'
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
    const [syncConfig, setSyncConfig] = useState({ excel_path: '', sheet_name: '', password: '' })
    const [availableSheets, setAvailableSheets] = useState<string[]>([])
    const [fetchingSheets, setFetchingSheets] = useState(false)

    const PROJECT_ID = 1

    useEffect(() => {
        fetchHistory()
    }, [])

    const fetchHistory = async () => {
        setLoading(true)
        try {
            const resp = await axios.get(`${HUB_URL}/sync/history/${PROJECT_ID}`)
            if (Array.isArray(resp.data)) {
                setHistory(resp.data)
            }
        } catch (e) {
            console.error("Hub connection failed")
        } finally {
            setLoading(false)
        }
    }

    const loadStateDetails = async (state: State) => {
        setSelectedState(state)
        setFetchingDetails(true)
        setDiffs([])
        setInspectData([])
        try {
            const [diffResp, snapResp] = await Promise.all([
                axios.get(`${HUB_URL}/sync/diff/${state.id}`),
                axios.get(`${HUB_URL}/sync/snapshot/${state.id}`)
            ])
            setDiffs(Array.isArray(diffResp.data) ? diffResp.data : [])
            setInspectData(Array.isArray(snapResp.data) ? snapResp.data : [])
        } catch (e) {
            console.error("Failed to load details")
        } finally {
            setFetchingDetails(false)
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
            await axios.post(`${AGENT_URL}/automation/sync-excel`, {
                project_id: PROJECT_ID,
                ...syncConfig
            })
            setShowSyncModal(false)
            fetchHistory()
        } catch (e: any) {
            alert("Sync Failed: " + (e.response?.data?.detail || e.message))
        } finally {
            setLoading(false)
        }
    }

    const groupedHistory: { [key: string]: State[] } = (Array.isArray(history) ? history : []).reduce((acc: any, state) => {
        const key = state.sheet_name || "Unknown Week"
        if (!acc[key]) acc[key] = []
        acc[key].push(state)
        return acc
    }, {})

    const handleBrowse = async () => {
        try {
            const resp = await axios.post(`${AGENT_URL}/automation/browse-file`)
            if (resp.data.path) setSyncConfig({ ...syncConfig, excel_path: resp.data.path })
        } catch (e) { alert("Agent not found.") }
    }

    return (
        <Row className="g-3">
            <Col md={3}>
                <Card className="shadow-sm border-0 bg-white" style={{ height: 'calc(100vh - 180px)', overflowY: 'auto' }}>
                    <Card.Header className="bg-primary text-white sticky-top d-flex justify-content-between align-items-center">
                        <strong>Project Timelines</strong>
                        <Button variant="light" size="sm" onClick={fetchHistory} disabled={loading}>⟳</Button>
                    </Card.Header>
                    <div className="d-grid p-2 border-bottom bg-white">
                        <Button variant="success" size="sm" onClick={() => setShowSyncModal(true)}>+ New Sync State</Button>
                    </div>
                    
                    <Accordion flush>
                        {Object.keys(groupedHistory).map((sheet, index) => (
                            <Accordion.Item eventKey={index.toString()} key={sheet}>
                                <Accordion.Header>
                                    <div className="d-flex justify-content-between w-100 me-3">
                                        <span className="fw-bold text-primary">📅 {sheet}</span>
                                        <Badge bg="secondary" pill>{groupedHistory[sheet].length}</Badge>
                                    </div>
                                </Accordion.Header>
                                <Accordion.Body className="p-0">
                                    <ListGroup variant="flush">
                                        {groupedHistory[sheet].map(state => (
                                            <ListGroup.Item 
                                                key={state.id} 
                                                action 
                                                active={selectedState?.id === state.id}
                                                onClick={() => loadStateDetails(state)}
                                                className="border-0 border-bottom py-2"
                                            >
                                                <div className="d-flex justify-content-between align-items-start">
                                                    <div>
                                                        <div className="fw-bold small">State #{state.id}</div>
                                                        <div className="text-muted" style={{fontSize: '0.7rem'}}>
                                                            {new Date(state.created_at).toLocaleString()}
                                                        </div>
                                                        <div className="mt-1">
                                                            <Badge bg="info" style={{fontSize: '0.65rem'}}>
                                                                👤 {state.excel_author || 'System'}
                                                            </Badge>
                                                        </div>
                                                    </div>
                                                    <Button variant="link" className="text-danger p-0 ms-2" onClick={(e) => { e.stopPropagation(); handleDelete(state.id); }}>×</Button>
                                                </div>
                                            </ListGroup.Item>
                                        ))}
                                    </ListGroup>
                                </Accordion.Body>
                            </Accordion.Item>
                        ))}
                    </Accordion>

                    {history.length === 0 && !loading && <div className="p-4 text-center text-muted small">No history on Hub.</div>}
                </Card>
            </Col>

            <Col md={9}>
                {selectedState ? (
                    <Card className="shadow-sm border-0" style={{ height: 'calc(100vh - 180px)' }}>
                        <Card.Header className="bg-dark text-white d-flex justify-content-between align-items-center">
                            <div>
                                <strong className="me-2">Week: {selectedState.sheet_name}</strong>
                                <Badge bg="primary">State #{selectedState.id}</Badge>
                            </div>
                            <div className="small text-info">Synced by {selectedState.created_by}</div>
                        </Card.Header>
                        <Card.Body className="p-0 d-flex flex-column bg-white">
                            <Tabs activeKey={activeViewTab} onSelect={(k) => setActiveViewTab(k || 'diffs')} className="bg-light px-2 pt-2 border-bottom">
                                <Tab eventKey="diffs" title={`📂 Changes (${diffs.length})`}>
                                    <div className="p-3" style={{ overflowY: 'auto', maxHeight: 'calc(100vh - 280px)' }}>
                                        {fetchingDetails ? (
                                            <div className="text-center p-5"><Spinner animation="border" className="me-2"/> Loading changes...</div>
                                        ) : (
                                            <DiffTable diffs={diffs} />
                                        )}
                                    </div>
                                </Tab>
                                <Tab eventKey="inspect" title="🔍 Full Data Inspector">
                                    <div style={{ height: 'calc(100vh - 280px)', position: 'relative' }}>
                                        {fetchingDetails ? (
                                            <div className="text-center p-5"><Spinner animation="border" className="me-2"/> Loading snapshot...</div>
                                        ) : (
                                            <DataGrid data={inspectData} />
                                        )}
                                    </div>
                                </Tab>
                            </Tabs>
                        </Card.Body>
                    </Card>
                ) : (
                    <div className="h-100 d-flex flex-column align-items-center justify-content-center text-muted border rounded bg-light border-dashed">
                        <i className="bi bi-clock-history mb-3" style={{fontSize: '3rem'}}></i>
                        <p>Select a state from the timeline.</p>
                    </div>
                )}
            </Col>

            <Modal show={showSyncModal} onHide={() => setShowSyncModal(false)}>
                <Modal.Header closeButton><Modal.Title>Sync Master Excel</Modal.Title></Modal.Header>
                <Modal.Body>
                    <Form>
                        <Form.Group className="mb-3">
                            <Form.Label>Excel File</Form.Label>
                            <InputGroup>
                                <Form.Control value={syncConfig.excel_path} readOnly placeholder="Browse..."/>
                                <Button variant="secondary" onClick={handleBrowse}>Browse</Button>
                            </InputGroup>
                        </Form.Group>
                        <Form.Group className="mb-3">
                            <Form.Label>Password</Form.Label>
                            <Form.Control type="password" value={syncConfig.password} onChange={e => setSyncConfig({...syncConfig, password: e.target.value})}/>
                        </Form.Group>
                        <Form.Group className="mb-3">
                            <Form.Label>Sheet</Form.Label>
                            <InputGroup>
                                <Form.Select value={syncConfig.sheet_name} onChange={e => setSyncConfig({...syncConfig, sheet_name: e.target.value})}>
                                    {availableSheets.map(s => <option key={s} value={s}>{s}</option>)}
                                </Form.Select>
                                <Button onClick={async () => {
                                    setFetchingSheets(true)
                                    try {
                                        const r = await axios.post(`${AGENT_URL}/automation/sheets`, { excel_path: syncConfig.excel_path, password: syncConfig.password })
                                        setAvailableSheets(r.data)
                                        if (r.data.length > 0) setSyncConfig(p => ({ ...p, sheet_name: r.data[0] }))
                                    } finally { setFetchingSheets(false) }
                                }}>{fetchingSheets ? <Spinner size="sm"/> : 'Refresh'}</Button>
                            </InputGroup>
                        </Form.Group>
                    </Form>
                </Modal.Body>
                <Modal.Footer><Button variant="success" onClick={runSync} disabled={!syncConfig.sheet_name || loading}>Start Push</Button></Modal.Footer>
            </Modal>
        </Row>
    )
}

function DiffTable({ diffs }: { diffs: Diff[] }) {
    if (diffs.length === 0) return <div className="p-4 text-center text-muted">No field changes (First Sync or No Edit).</div>
    return (
        <Table size="sm" hover className="small border shadow-sm">
            <thead className="table-light"><tr><th>Pg</th><th>Product</th><th>Field</th><th>Old Value</th><th>New Value</th></tr></thead>
            <tbody>
                {diffs.map((d, i) => (
                    <tr key={i}>
                        <td><Badge bg="secondary">{d.page}</Badge></td>
                        <td className="fw-bold">{d.product}</td>
                        <td className="text-muted small">{d.field}</td>
                        <td className="text-danger text-decoration-line-through">{d.old}</td>
                        <td className="text-success fw-bold">{d.new}</td>
                    </tr>
                ))}
            </tbody>
        </Table>
    )
}
