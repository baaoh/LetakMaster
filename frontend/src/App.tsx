import { useState, useEffect } from 'react'
import { Container, Tabs, Tab } from 'react-bootstrap'
import { BrowserRouter as Router, Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import { DataInputTab } from './components/DataInputTab'
import { TraceabilityTab } from './components/TraceabilityTab'
import { QATab } from './components/QATab'
import { QAInspectView } from './components/QAInspectView'
import axios from 'axios'

const API_BASE = "http://127.0.0.1:8000"

function Dashboard() {
  const navigate = useNavigate();
  const location = useLocation();
  const [canQA, setCanQA] = useState(false);

  // Determine active tab from URL or default to 'data'
  const activeTab = location.pathname.startsWith('/qa') ? 'qa' : 
                    location.pathname.startsWith('/trace') ? 'trace' : 'data';

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const resp = await axios.get(`${API_BASE}/history`);
        // Enable QA if there is at least one sync/automation state
        if (resp.data && resp.data.length > 0) {
          setCanQA(true);
        }
      } catch (e) {
        console.error("Failed to check project status", e);
      }
    };
    checkStatus();
  }, []);

  const handleSelect = (key: string | null) => {
    if (key === 'qa') navigate('/qa');
    else if (key === 'trace') navigate('/trace');
    else navigate('/');
  };

  return (
    <Container fluid className="py-4">
      <h1 className="mb-4">LetakMaster Dashboard</h1>
      
      <Tabs 
        activeKey={activeTab} 
        id="main-tabs" 
        className="mb-3"
        onSelect={handleSelect}
      >
        <Tab eventKey="data" title="Data Input & History">
          <DataInputTab />
        </Tab>
        <Tab eventKey="trace" title="Traceability & Search">
          <TraceabilityTab />
        </Tab>
        <Tab eventKey="qa" title="Leták checker" disabled={!canQA}>
          {canQA ? <QATab /> : (
            <div className="p-5 text-center text-muted">
              Please sync an Excel file and run Layout Automation first.
            </div>
          )}
        </Tab>
      </Tabs>
    </Container>
  )
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/qa/inspect" element={<QAInspectView />} />
        <Route path="/qa" element={<Dashboard />} />
        <Route path="/trace" element={<Dashboard />} />
        <Route path="/" element={<Dashboard />} />
      </Routes>
    </Router>
  )
}

export default App

