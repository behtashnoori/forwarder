import React, { useEffect } from 'react';
import { Navigate, useLocation } from 'react-router';
import { rememberCurrentRouteForLogin } from '@/lib/authContinuity';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: string[];
  unauthorizedTo?: string;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles, unauthorizedTo = "/expert" }) => {
  const expertUser = localStorage.getItem('expert_user');
  const expertToken = localStorage.getItem('expert_token');
  const location = useLocation();
  const needsLogin = !expertUser || !expertToken || expertToken === 'null';

  useEffect(() => {
    if (needsLogin) rememberCurrentRouteForLogin();
  }, [needsLogin, location.pathname, location.search, location.hash]);
  
  if (needsLogin) {
    return <Navigate to="/" replace />;
  }

  if (allowedRoles?.length) {
    try {
      const user = JSON.parse(expertUser);
      if (!allowedRoles.includes(user.role)) {
        return <Navigate to={unauthorizedTo} replace />;
      }
    } catch (error) {
      return <Navigate to="/" replace />;
    }
  }
  
  return <>{children}</>;
};

export default ProtectedRoute;


