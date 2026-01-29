import React, { useState } from 'react';
import { Button, Card, Row, Col, ProgressBar, Badge, Alert } from 'react-bootstrap';
import axios from 'axios';

const API_BASE = "http://127.0.0.1:8000";

interface PSDRotationResult {
    page: string;
    json_path: string;
    preview_path: string;
    group_count: number;
}

export const QATab: React.FC = () => {
    const [importing, setImporting] = useState(false);
    const [checking, setChecking] = useState(false);
    const [results, setResults] = useState<PSDRotationResult[]>([]);
    const [error, setError] = useState<string | null>(null);
    const [message, setMessage] = useState<string | null>(null);

    const handleImportFolder = async () => {
        setImporting(true);
        setError(null);
        setMessage(null);
        try {
            // First browse for folder
            const browseResp = await axios.post(`${API_BASE}/system/browse-folder`);
            const path = browseResp.data.path;
            
            if (!path) {
                setImporting(false);
                return;
            }

            const importResp = await axios.post(`${API_BASE}/qa/import-folder`, { folder_path: path });
            setResults(importResp.data.results);
            setMessage(`Successfully imported ${importResp.data.results.length} PSD files.`);
        } catch (err: any) {
            setError(err.response?.data?.detail || err.message);
        } finally {
            setImporting(false);
        }
    };

    const handleRunCheck = async () => {
        setChecking(true);
        setError(null);
        setMessage(null);
        try {
            const resp = await axios.post(`${API_BASE}/qa/check`);
            setMessage(resp.data.message);
        } catch (err: any) {
            setError(err.response?.data?.detail || err.message);
        } finally {
            setChecking(false);
        }
    };

    return (
        <div className="p-3">
            <Card className="mb-4 shadow-sm">
                <Card.Body>
                    <h3>Leták Checker (QA)</h3>
                    <p className="text-muted">
                        Import your designed PSD files to compare them against the Master Excel.
                        Discrepancies will be highlighted in orange within Excel.
                    </p>
                    <div className="d-flex gap-2">
                        <Button 
                            variant="primary" 
                            onClick={handleImportFolder} 
                            disabled={importing || checking}
                        >
                            {importing ? "Importing..." : "Import PSD Folder"}
                        </Button>
                        <Button 
                            variant="success" 
                            onClick={handleRunCheck} 
                            disabled={importing || checking || results.length === 0}
                        >
                            {checking ? "Checking..." : "Run Comparison Check"}
                        </Button>
                    </div>
                </Card.Body>
            </Card>

            {error && <Alert variant="danger">{error}</Alert>}
            {message && <Alert variant="success">{message}</Alert>}

            {importing && (
                <div className="my-4">
                    <p>Processing PSD files... (this uses psd-tools and may take a moment)</p>
                    <ProgressBar animated now={100} />
                </div>
            )}

            {results.length > 0 && (
                <Row className="g-3">
                    {results.map((res, idx) => (
                        <Col key={idx} md={3}>
                            <Card className="h-100 shadow-sm">
                                <Card.Img 
                                    variant="top" 
                                    src={`${API_BASE}/previews/${res.page}.png?t=${new Date().getTime()}`} 
                                    style={{ height: '200px', objectFit: 'cover' }}
                                />
                                <Card.Body className="p-2 text-center">
                                    <Card.Title className="small mb-1">{res.page}</Card.Title>
                                    <Badge bg="info">{res.group_count} Groups Found</Badge>
                                </Card.Body>
                            </Card>
                        </Col>
                    ))}
                </Row>
            )}
        </div>
    );
};
