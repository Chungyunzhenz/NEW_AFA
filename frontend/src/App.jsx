import { Routes, Route } from 'react-router-dom';
import MainLayout from './components/layout/MainLayout';
import DashboardPage from './pages/DashboardPage';
import TradingAnalysisPage from './pages/TradingAnalysisPage';
import ForecastPage from './pages/ForecastPage';
import DataManagementPage from './pages/DataManagementPage';

function App() {
  return (
    <MainLayout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/trading" element={<TradingAnalysisPage />} />
        <Route path="/forecast" element={<ForecastPage />} />
        <Route path="/data" element={<DataManagementPage />} />
      </Routes>
    </MainLayout>
  );
}

export default App;
