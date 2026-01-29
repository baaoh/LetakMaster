import React, { useEffect, useState, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import axios from 'axios';
import { Spinner, Alert, Container, Button } from 'react-bootstrap';

const API_BASE = "http://127.0.0.1:8000";

export const QAInspectView: React.FC = () => {
    const [searchParams] = useSearchParams();
    const page = searchParams.get("page");
    const group = searchParams.get("group");

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [data, setData] = useState<any>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        if (!page || !group) {
            setError("Missing page or group parameter");
            setLoading(false);
            return;
        }

        const fetchData = async () => {
            try {
                const resp = await axios.get(`${API_BASE}/qa/inspect?page=${page}&group=${group}`);
                setData(resp.data);
            } catch (err: any) {
                setError("Failed to load inspection data");
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [page, group]);

    useEffect(() => {
        if (data && canvasRef.current) {
            const canvas = canvasRef.current;
            const ctx = canvas.getContext('2d');
            if (!ctx) return;

            const img = new Image();
            img.src = `${API_BASE}${data.preview_url}`;
            img.onload = () => {
                // Set canvas size to match image aspect ratio but scale to fit screen
                const maxWidth = window.innerWidth * 0.9;
                const scale = maxWidth / img.width;
                canvas.width = img.width * scale;
                canvas.height = img.height * scale;

                // Draw main image
                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

                // Draw Dark Overlay
                ctx.fillStyle = "rgba(0, 0, 0, 0.7)";
                ctx.fillRect(0, 0, canvas.width, canvas.height);

                // Spotlight Cutout
                // Coords from PSD are [left, top, right, bottom] in original pixels
                if (data.coords) {
                    const [left, top, right, bottom] = data.coords;
                    const x = left * scale;
                    const y = top * scale;
                    const w = (right - left) * scale;
                    const h = (bottom - top) * scale;

                    // Clear the cutout
                    // To make it look "bright", we redraw that portion of the image without overlay
                    ctx.save();
                    ctx.beginPath();
                    ctx.rect(x - 10, y - 10, w + 20, h + 20); // Add small padding
                    ctx.clip();
                    ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                    ctx.restore();

                    // Draw Border around spotlight
                    ctx.strokeStyle = "#ff9900";
                    ctx.lineWidth = 3;
                    ctx.strokeRect(x - 10, y - 10, w + 20, h + 20);
                }
            };
        }
    }, [data]);

    if (loading) return <Container className="text-center py-5"><Spinner animation="border" /></Container>;
    if (error) return <Container className="py-5"><Alert variant="danger">{error}</Alert></Container>;

    return (
        <Container fluid className="py-4 bg-dark min-vh-100 text-light text-center">
            <div className="mb-3 d-flex justify-content-between align-items-center">
                <h3>Inspecting: {group} (Page {page})</h3>
                <Button variant="outline-light" onClick={() => window.close()}>Close Window</Button>
            </div>
            <div style={{ overflow: 'auto' }}>
                <canvas ref={canvasRef} className="shadow-lg border border-secondary" />
            </div>
        </Container>
    );
};
