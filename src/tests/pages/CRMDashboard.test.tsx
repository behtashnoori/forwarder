import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import CRMDashboard from '../../pages/CRMDashboard';

vi.mock('../../i18n', () => ({
  useI18n: () => ({
    t: (key: string) => key,
  }),
}));

vi.mock('../../components/PageNav', () => ({
  default: ({ backLabel }: { backLabel?: string }) => (
    <nav aria-label="page navigation">{backLabel}</nav>
  ),
}));

describe('CRMDashboard', () => {
  it('renders the current placeholder CRM surface', () => {
    render(<CRMDashboard />);

    expect(screen.getByRole('heading', { name: 'crm.title' })).toBeInTheDocument();
    expect(screen.getByText('crm.inDevelopment')).toBeInTheDocument();
    expect(screen.getByLabelText('page navigation')).toHaveTextContent('common.back');
  });
});
