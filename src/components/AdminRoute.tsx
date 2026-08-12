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
    if (user.authority !== 'PLATFORM_ADMIN' && user.authority !== 'ORGANIZATION_ADMIN' && user.role !== 'admin') {
      return <Navigate to="/expert" replace />;
    }
  } catch (error) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
};

export default AdminRoute;
