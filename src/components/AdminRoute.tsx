import React from 'react';
import { Navigate } from 'react-router';

interface AdminRouteProps {
  children: React.ReactNode;
}

const AdminRoute: React.FC<AdminRouteProps> = ({ children }) => {
  const expertUser = localStorage.getItem('expert_user');
  const expertToken = localStorage.getItem('expert_token');

  if (!expertUser || !expertToken || expertToken === 'null') {
    return <Navigate to="/" replace />;
  }

  try {
    const user = JSON.parse(expertUser);
    if (user.role !== 'admin') {
      return <Navigate to="/expert" replace />;
    }
  } catch (error) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};

export default AdminRoute;
