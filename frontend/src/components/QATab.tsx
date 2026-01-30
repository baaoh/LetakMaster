import React, { useState, useEffect } from 'react';
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
    const [progress, setProgress] = useState({ current: 0, total: 0, file: "" });

    // Load existing scans on mount
    useEffect(() => {
        axios.get(`${API_BASE}/qa/scans`)
            .then(res => setResults(res.data))
            .catch(err => console.error("Failed to load existing scans", err));
    }, []);

    const handleImportFolder = async () => {
        setImporting(true);
        setError(null);
        setMessage(null);
        setProgress({ current: 0, total: 0, file: "" });
        
        try {
            // First browse for folder
            const browseResp = await axios.post(`${API_BASE}/system/browse-folder`);
            const path = browseResp.data.path;
            
            if (!path) {
                setImporting(false);
                return;
            }

            // Use Fetch API for Streaming Response
            const response = await fetch(`${API_BASE}/qa/import-folder`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ folder_path: path })
            });

            if (!response.body) throw new Error("No response body");

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";

            while (true) {
                const { value, done } = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split("\n");
                buffer = lines.pop() || ""; // Keep incomplete line

                for (const line of lines) {
                    if (!line.trim()) continue;
                    try {
                        const msg = JSON.parse(line);
                        if (msg.type === "start") {
                            setProgress({ current: 0, total: msg.total, file: "Starting..." });
                        } else if (msg.type === "progress") {
                            setProgress({ current: msg.current, total: msg.total, file: msg.file });
                        } else if (msg.type === "result") {
                            setResults(prev => [...prev, msg.data]);
                        } else if (msg.type === "complete") {
                            setMessage(msg.message);
                        } else if (msg.type === "error") {
                            setError(msg.message);
                        }
                    } catch (e) {
                        console.error("JSON Parse Error", e);
                    }
                }
            }

        } catch (err: any) {
            setError(err.message);
        } finally {
            setImporting(false);
            // Refresh list to ensure order
            axios.get(`${API_BASE}/qa/scans`).then(res => setResults(res.data));
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
                <div className="my-4 card p-3 bg-light">
                    <h5>Processing: {progress.file}</h5>
                    <ProgressBar 
                        animated 
                        now={progress.total > 0 ? (progress.current / progress.total) * 100 : 0} 
                        label={`${progress.current} / ${progress.total}`}
                    />
                </div>
            )}

            {results.length > 0 && (
                <div>
                    <h5 className="mb-3">Imported Pages ({results.length})</h5>
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
                                        <Badge bg={res.group_count > 0 ? "info" : "warning"}>
                                            {res.group_count} Groups Found
                                        </Badge>
                                    </Card.Body>
                                </Card>
                            </Col>
                        ))}
                    </Row>
                </div>
            )}
        </div>
    );
};