import { Container, Tabs, Tab, Badge } from 'react-bootstrap'
import { BrowserRouter as Router, Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import { CollaborationTab } from './components/CollaborationTab'
import { DesignerTab } from './components/DesignerTab'
import { TraceabilityTab } from './components/TraceabilityTab'
import { QATab } from './components/QATab'
import { QAInspectView } from './components/QAInspectView'

function Dashboard() {
  const navigate = useNavigate();
  const location = useLocation();

  const activeTab = location.pathname.startsWith('/qa') ? 'qa' : 
                    location.pathname.startsWith('/trace') ? 'trace' : 
                    location.pathname.startsWith('/design') ? 'design' : 'shared';

  const handleSelect = (key: string | null) => {
    if (key === 'qa') navigate('/qa');
    else if (key === 'trace') navigate('/trace');
    else if (key === 'design') navigate('/design');
    else navigate('/');
  };

  return (
    <Container fluid className="py-4">
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div>
            <h1 className="m-0">LetakMaster <span className="text-primary">v2.0</span></h1>
            <small className="text-muted">Connected to Synology Hub: 192.168.4.222</small>
        </div>
        <Badge bg="success" className="p-2">Collaborative Hub Active</Badge>
      </div>
      
      <Tabs 
        activeKey={activeTab} 
        id="main-tabs" 
        className="mb-4 custom-main-tabs"
        onSelect={handleSelect}
        variant="pills"
      >
        <Tab eventKey="shared" title="🌍 Shared History & Timeline">
          <CollaborationTab />
        </Tab>
        <Tab eventKey="design" title="🎨 Flyer Designer Workspace">
          <DesignerTab />
        </Tab>
        <Tab eventKey="trace" title="🔍 Data Traceability">
          <TraceabilityTab />
        </Tab>
        <Tab eventKey="qa" title="✅ Leták Checker (QA)">
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
        <Route path="/design" element={<Dashboard />} />
        <Route path="/" element={<Dashboard />} />
      </Routes>
    </Router>
  )
}

export default App
