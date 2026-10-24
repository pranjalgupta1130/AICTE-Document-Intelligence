import React from 'react';
import { LoginScreen } from '../components/LoginScreen';
import { AuthSession } from '../types/auth';

interface LoginPageProps {
  onLoginSuccess?: (session: AuthSession) => void;
}

export const LoginPage: React.FC<LoginPageProps> = ({ onLoginSuccess }) => {
  return <LoginScreen onLoginSuccess={onLoginSuccess} />;
};

export default LoginPage;
