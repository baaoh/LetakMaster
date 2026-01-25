import { useState } from 'react'
import { Form, Button, Table, Badge, Modal, Spinner, Alert } from 'react-bootstrap'
import axios from 'axios'

const API_BASE = 'http://localhost:8000'

interface SearchResult {
    id: number
    date: string
    state_id: number
    page: number
    product: string
    supplier: string
    ean: string
    slot: string
}

export function TraceabilityTab() {
    const [query, setQuery] = useState('')
    const [results, setResults] = useState<SearchResult[]>([])
    const [loading, setLoading] = useState(false)
    const [scanning, setScanning] = useState(false)
    
    // Preview Modal
    const [showModal, setShowModal] = useState(false)
    const [previewPage, setPreviewPage] = useState<number | null>(null)
    const [previewError, setPreviewError] = useState<string | null>(null)

    const handleSearch = async (e?: React.FormEvent) => {
        if (e) e.preventDefault()
        if (!query.trim()) return
        
        setLoading(true)
        try {
            const resp = await axios.get(`${API_BASE}/products/search`, { params: { q: query } })
            setResults(resp.data)
        } catch (err) {
            console.error(err)
            alert("Search failed")
        } finally {
            setLoading(false)
        }
    }

    const handleScan = async () => {
        setScanning(true)
        try {
            await axios.post(`${API_BASE}/system/render-previews`)
            alert("Scan & Render complete!")
        } catch (err) {
            console.error(err)
            alert("Scan failed. Check backend logs.")
        } finally {
            setScanning(false)
        }
    }

    const openPreview = (page: number) => {
        setPreviewPage(page)
        setPreviewError(null)
        setShowModal(true)
    }

    return (
        <div className="p-3 bg-white border rounded" style={{ minHeight: '600px' }}>
            <div className="d-flex justify-content-between mb-4">
                <Form onSubmit={handleSearch} className="d-flex gap-2" style={{ width: '60%' }}>
                    <Form.Control 
                        type="text" 
                        placeholder="Search Product, Supplier, or EAN..." 
                        value={query}
                        onChange={e => setQuery(e.target.value)}
                    />
                    <Button type="submit" variant="primary" disabled={loading}>
                        {loading ? <Spinner size="sm" animation="border" /> : 'Search'}
                    </Button>
                </Form>
                
                <Button variant="outline-secondary" onClick={handleScan} disabled={scanning}>
                    {scanning ? <Spinner size="sm" animation="border" /> : 'Scan & Render PSDs'}
                </Button>
            </div>

            <Table hover responsive>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Page</th>
                        <th>Product</th>
                        <th>Supplier</th>
                        <th>EAN</th>
                        <th>Slot</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {results.map(row => (
                        <tr key={row.id}>
                            <td>{new Date(row.date).toLocaleDateString()}</td>
                            <td><Badge bg="info">{row.page}</Badge></td>
                            <td className="fw-bold">{row.product}</td>
                            <td className="text-muted">{row.supplier}</td>
                            <td><small>{row.ean}</small></td>
                            <td><small>{row.slot}</small></td>
                            <td>
                                <Button size="sm" variant="outline-primary" onClick={() => openPreview(row.page)}>
                                    View Page
                                </Button>
                            </td>
                        </tr>
                    ))}
                    {results.length === 0 && !loading && (
                        <tr>
                            <td colSpan={7} className="text-center text-muted p-4">
                                No results found. Try searching for a product name.
                            </td>
                        </tr>
                    )}
                </tbody>
            </Table>

            <Modal show={showModal} onHide={() => setShowModal(false)} size="xl" centered>
                <Modal.Header closeButton>
                    <Modal.Title>Page {previewPage} Preview</Modal.Title>
                </Modal.Header>
                <Modal.Body className="text-center bg-light" style={{ minHeight: '400px' }}>
                    {previewPage && (
                        <img 
                            src={`${API_BASE}/pages/${previewPage}/preview`} 
                            alt={`Page ${previewPage}`} 
                            className="img-fluid border shadow-sm"
                            onError={() => setPreviewError("Preview not available. Please run 'Scan & Render PSDs'.")}
                        />
                    )}
                    {previewError && (
                        <Alert variant="warning" className="mt-3">{previewError}</Alert>
                    )}
                </Modal.Body>
            </Modal>
        </div>
    )
}
