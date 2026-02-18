import { useState, useEffect } from 'react'
import { Container, Tabs, Tab, Badge } from 'react-bootstrap'
import { BrowserRouter as Router, Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import { CollaborationTab } from './components/CollaborationTab'
import { DataInputTab } from './components/DataInputTab'
import { TraceabilityTab } from './components/TraceabilityTab'
import { QATab } from './components/QATab'
import { QAInspectView } from './components/QAInspectView'

function Dashboard() {
  const navigate = useNavigate();
  const location = useLocation();

  // Determine active tab from URL or default to 'shared'
  const activeTab = location.pathname.startsWith('/qa') ? 'qa' : 
                    location.pathname.startsWith('/trace') ? 'trace' : 
                    location.pathname.startsWith('/local') ? 'local' : 'shared';

  const handleSelect = (key: string | null) => {
    if (key === 'qa') navigate('/qa');
    else if (key === 'trace') navigate('/trace');
    else if (key === 'local') navigate('/local');
    else navigate('/');
  };

  return (
    <Container fluid className="py-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h1 className="m-0">LetakMaster <span className="text-primary">v2.0</span></h1>
        <Badge bg="success">Collaborative Mode Active</Badge>
      </div>
      
      <Tabs 
        activeKey={activeTab} 
        id="main-tabs" 
        className="mb-3"
        onSelect={handleSelect}
      >
        <Tab eventKey="shared" title="🌍 Shared History & Diffs">
          <CollaborationTab />
        </Tab>
        <Tab eventKey="local" title="💻 Local Workspace (Legacy)">
          <DataInputTab />
        </Tab>
        <Tab eventKey="trace" title="🔍 Traceability">
          <TraceabilityTab />
        </Tab>
        <Tab eventKey="qa" title="✅ Leták Checker">
          <QATab />
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
