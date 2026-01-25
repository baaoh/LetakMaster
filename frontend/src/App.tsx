import { Container, Tabs, Tab } from 'react-bootstrap'
import { DataInputTab } from './components/DataInputTab'
import { TraceabilityTab } from './components/TraceabilityTab'

function App() {
  return (
    <Container fluid className="py-4">
      <h1 className="mb-4">LetakMaster Dashboard</h1>
      
      <Tabs defaultActiveKey="data" id="main-tabs" className="mb-3">
        <Tab eventKey="data" title="Data Input & History">
          <DataInputTab />
        </Tab>
        <Tab eventKey="trace" title="Traceability & Search">
          <TraceabilityTab />
        </Tab>
        <Tab eventKey="design" title="Design & Layers">
          <div className="p-3 border rounded bg-light text-center text-muted">
            Design tools coming soon...
          </div>
        </Tab>
      </Tabs>
    </Container>
  )
}

export default App
