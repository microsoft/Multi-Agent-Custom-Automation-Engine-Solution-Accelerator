import React from 'react';
import './App.css';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { HomePage, PlanPage, AnalyticsDashboard, SimpleHomePage, SimplePlanPage } from './pages';
import { useWebSocket } from './hooks/useWebSocket';

function App() {
    const { isConnected, isConnecting, error } = useWebSocket();
    
  return (
    <Router>
      <Routes>
        {/* Simple Mode (Default) */}
        <Route path="/" element={<SimpleHomePage />} />
        <Route path="/simple" element={<SimpleHomePage />} />
        <Route path="/plan/:planId" element={<SimplePlanPage />} />
        <Route path="/simple/plan/:planId" element={<SimplePlanPage />} />
        
        {/* Advanced Mode */}
        <Route path="/advanced" element={<HomePage />} />
        <Route path="/advanced/plan/:planId" element={<PlanPage />} />
        
        {/* Analytics */}
        <Route path="/analytics" element={<AnalyticsDashboard />} />
        
        {/* Default fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;