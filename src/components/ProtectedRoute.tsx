import React from 'react';
import { Navigate } from 'react-router-dom';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRoles?: string[];
  unauthorizedTo?: string;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles, unauthorizedTo = "/expert" }) => {
  const expertUser = localStorage.getItem('expert_user');
  const expertToken = localStorage.getItem('expert_token');
  
  if (!expertUser || !expertToken || expertToken === 'null') {
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


