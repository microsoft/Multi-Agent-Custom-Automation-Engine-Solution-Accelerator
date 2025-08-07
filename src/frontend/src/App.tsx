import React from 'react';
import './App.css';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { HomePage, PlanPage, PlanCreatePage } from './pages';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/plan/:planId/create/:teamId?" element={<PlanCreatePage />} />
        <Route path="/plan/:planId" element={<PlanPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;