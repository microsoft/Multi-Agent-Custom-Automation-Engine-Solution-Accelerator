import React, { useEffect } from 'react';
import './App.css';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { HomePage, PlanPage } from './pages';
import { useWebSocket } from './hooks/useWebSocket';
import { useAppDispatch } from './store/hooks';
import { hydrateCurrentUser } from './store/slices/appSlice';
import { getUserInfoGlobal } from './api/config';

function App() {
    useWebSocket();
    const dispatch = useAppDispatch();

    useEffect(() => {
        dispatch(hydrateCurrentUser(getUserInfoGlobal()));
    }, [dispatch]);
    
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/plan/:planId" element={<PlanPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Router>
  );
}

export default App;