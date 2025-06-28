import { ConfigProvider } from 'antd';
import ptBR from 'antd/locale/pt_BR';
import React from 'react';
import { Navigate, Route, BrowserRouter as Router, Routes } from 'react-router-dom';
import './App.css';
import AppLayout from './components/AppLayout';
import Apartments from './pages/Apartments';
import Buildings from './pages/Buildings';
import Dashboard from './pages/Dashboard';
import Furnitures from './pages/Furnitures';
import Leases from './pages/Leases';
import Tenants from './pages/Tenants';

const App: React.FC = () => {
  return (
    <ConfigProvider locale={ptBR}>
      <Router>
        <AppLayout>
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/buildings" element={<Buildings />} />
            <Route path="/apartments" element={<Apartments />} />
            <Route path="/tenants" element={<Tenants />} />
            <Route path="/furnitures" element={<Furnitures />} />
            <Route path="/leases" element={<Leases />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </AppLayout>
      </Router>
    </ConfigProvider>
  );
};

export default App;
