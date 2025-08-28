import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import { ProtectedRoute, Layout } from './components';
import { WelcomePage } from './pages/WelcomePage';
import { HomePage } from './pages/HomePage';
import { UploadPage } from './pages/UploadPage';
import LectureViewPage from './pages/LectureViewPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { OAuthCallbackPage } from './pages/OAuthCallbackPage';
import { SubscriptionPage } from './pages/SubscriptionPage';
import { PaymentSuccessPage } from './pages/PaymentSuccessPage';
import { PaymentCancelPage } from './pages/PaymentCancelPage';

function App() {
  return (
    <Router>
      <AuthProvider>
        <div className="w-full min-h-screen flex flex-col bg-gray-50">
          <Layout>
              <Routes>
                <Route path="/" element={<WelcomePage />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />
                <Route path="/oauth/callback" element={<OAuthCallbackPage />} />
                <Route 
                  path="/dashboard" 
                  element={
                    <ProtectedRoute>
                      <HomePage />
                    </ProtectedRoute>
                  } 
                />
                <Route 
                  path="/upload" 
                  element={
                    <ProtectedRoute>
                      <UploadPage />
                    </ProtectedRoute>
                  } 
                />
                <Route 
                  path="/lecture/:id" 
                  element={
                    <ProtectedRoute>
                      <LectureViewPage />
                    </ProtectedRoute>
                  } 
                />
                <Route 
                  path="/subscription" 
                  element={
                    <ProtectedRoute>
                      <SubscriptionPage />
                    </ProtectedRoute>
                  } 
                />
                <Route 
                  path="/payment-success" 
                  element={
                    <ProtectedRoute>
                      <PaymentSuccessPage />
                    </ProtectedRoute>
                  } 
                />
                <Route 
                  path="/payment-cancel" 
                  element={
                    <ProtectedRoute>
                      <PaymentCancelPage />
                    </ProtectedRoute>
                  } 
                />
              </Routes>
            </Layout>
          </div>
        </AuthProvider>
      </Router>
  );
}

export default App;