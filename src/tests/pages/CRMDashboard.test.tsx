import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import CRMDashboard from '../../pages/CRMDashboard';
import * as api from '../../lib/api';

// Mock the API functions
vi.mock('../../lib/api', () => ({
  fetchCRMDashboardKPIs: vi.fn(),
  fetchCustomers: vi.fn(),
  fetchOpportunities: vi.fn(),
  fetchActivities: vi.fn(),
}));

// Mock the toast hook
vi.mock('../../hooks/use-toast', () => ({
  useToast: () => ({
    toast: vi.fn(),
  }),
}));

describe('CRMDashboard', () => {
  const mockKPIs = {
    customers: {
      total: 100,
      new_this_month: 10
    },
    opportunities: {
      total: 50,
      open: 30,
      won: 15,
      pipeline_value: 1000000
    },
    activities: {
      total: 200,
      completed: 150
    },
    recent_activities: [
      {
        id: 1,
        type: 'call',
        subject: 'Customer call',
        customer_name: 'John Doe',
        expert_name: 'Expert 1',
        created_at: '2024-01-01T00:00:00Z'
      }
    ]
  };

  const mockCustomers = {
    customers: [
      {
        id: 1,
        name: 'John Doe',
        company_name: 'Acme Corp',
        email: 'john@acme.com',
        phone: '1234567890',
        customer_type: 'customer',
        status: 'active',
        industry: 'Technology',
        last_contact_at: '2024-01-01T00:00:00Z',
        created_at: '2024-01-01T00:00:00Z',
        total_opportunities: 5,
        total_activities: 10
      }
    ],
    pagination: {
      page: 1,
      per_page: 10,
      total: 1,
      pages: 1,
      has_next: false,
      has_prev: false
    }
  };

  beforeEach(() => {
    vi.clearAllMocks();
    
    // Mock successful API responses
    vi.mocked(api.fetchCRMDashboardKPIs).mockResolvedValue(mockKPIs);
    vi.mocked(api.fetchCustomers).mockResolvedValue(mockCustomers);
    vi.mocked(api.fetchOpportunities).mockResolvedValue({
      opportunities: [],
      pagination: { page: 1, per_page: 10, total: 0, pages: 0, has_next: false, has_prev: false }
    });
    vi.mocked(api.fetchActivities).mockResolvedValue({
      activities: [],
      pagination: { page: 1, per_page: 10, total: 0, pages: 0, has_next: false, has_prev: false }
    });
  });

  it('renders dashboard title', async () => {
    render(<CRMDashboard />);
    
    expect(screen.getByText('داشبورد CRM')).toBeInTheDocument();
    expect(screen.getByText('مدیریت مشتریان، فروش و فعالیت‌ها')).toBeInTheDocument();
  });

  it('displays KPI cards', async () => {
    render(<CRMDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('کل مشتریان')).toBeInTheDocument();
      expect(screen.getByText('100')).toBeInTheDocument();
      expect(screen.getByText('فرصت‌های باز')).toBeInTheDocument();
      expect(screen.getByText('30')).toBeInTheDocument();
    });
  });

  it('displays recent activities', async () => {
    render(<CRMDashboard />);
    
    await waitFor(() => {
      expect(screen.getByText('فعالیت‌های اخیر')).toBeInTheDocument();
      expect(screen.getByText('Customer call')).toBeInTheDocument();
    });
  });

  it('renders tab navigation', async () => {
    render(<CRMDashboard />);
    
    expect(screen.getByText('مشتریان')).toBeInTheDocument();
    expect(screen.getByText('فرصت‌های فروش')).toBeInTheDocument();
    expect(screen.getByText('فعالیت‌ها')).toBeInTheDocument();
  });

  it('handles loading state', () => {
    // Mock loading state by not resolving promises immediately
    vi.mocked(api.fetchCRMDashboardKPIs).mockImplementation(() => new Promise(() => {}));
    
    render(<CRMDashboard />);
    
    // Should show loading spinner or similar
    expect(screen.getByText('داشبورد CRM')).toBeInTheDocument();
  });

  it('handles API errors gracefully', async () => {
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    
    vi.mocked(api.fetchCRMDashboardKPIs).mockRejectedValue(new Error('API Error'));
    
    render(<CRMDashboard />);
    
    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalled();
    });
    
    consoleSpy.mockRestore();
  });

  it('formats currency correctly', async () => {
    render(<CRMDashboard />);
    
    await waitFor(() => {
      // Check if currency is formatted with Persian numbers
      expect(screen.getByText(/1,000,000/)).toBeInTheDocument();
    });
  });

  it('displays customer information correctly', async () => {
    render(<CRMDashboard />);
    
    // Switch to customers tab
    const customersTab = screen.getByText('مشتریان');
    customersTab.click();
    
    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
      expect(screen.getByText('john@acme.com')).toBeInTheDocument();
    });
  });

  it('shows empty state when no data', async () => {
    vi.mocked(api.fetchCustomers).mockResolvedValue({
      customers: [],
      pagination: { page: 1, per_page: 10, total: 0, pages: 0, has_next: false, has_prev: false }
    });
    
    render(<CRMDashboard />);
    
    const customersTab = screen.getByText('مشتریان');
    customersTab.click();
    
    await waitFor(() => {
      expect(screen.getByText('مشتری یافت نشد')).toBeInTheDocument();
    });
  });
});
