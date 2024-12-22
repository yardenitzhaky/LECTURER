import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Layout } from './components/Layout';
import { HomePage } from './pages/HomePage';
import { UploadPage } from './pages/UploadPage';
import LectureViewPage from './pages/LectureViewPage';

function App() {
  return (
    <Router>
      <div className="w-full min-h-screen flex flex-col bg-gray-50">
        <Layout>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/upload" element={<UploadPage />} />
            <Route path="/lecture/:id" element={<LectureViewPage />} />
          </Routes>
        </Layout>
      </div>
    </Router>
  );
}

export default App;