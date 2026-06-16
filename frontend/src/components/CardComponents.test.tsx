import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import ItemCard from './ItemCard';
import RequestCard from './RequestCard';
import { ItemOut, RequestOut } from '@/types';

// Mock lucide-react to prevent ESM import/render issues in Jest
jest.mock('lucide-react', () => ({
  MapPin: () => <span data-testid="map-pin" />,
  Calendar: () => <span data-testid="calendar" />,
  Layers: () => <span data-testid="layers" />,
  Activity: () => <span data-testid="activity" />,
  Phone: () => <span data-testid="phone" />,
  User: () => <span data-testid="user" />,
  MessageSquare: () => <span data-testid="message-square" />,
  AlertCircle: () => <span data-testid="alert-circle" />,
}));

const mockItem: ItemOut = {
  id: 42,
  donor_id: 1,
  donor_name: 'Jane Doe',
  title: 'Warm Winter Coat',
  description: 'A warm wool winter coat in excellent condition.',
  category: 'clothing',
  condition: 'like_new',
  quantity: 2,
  status: 'available',
  city: 'Test City',
  pincode: '123456',
  image_url: 'http://example.com/coat.jpg',
  donated_at: null,
  removed_at: null,
  created_at: '2026-06-15T00:00:00Z',
  updated_at: '2026-06-15T00:00:00Z',
};

const mockRequest: RequestOut = {
  id: 10,
  item_id: 42,
  requester_id: 2,
  item_title: 'Warm Winter Coat',
  donor_name: 'Jane Doe',
  donor_phone: '555-1234',
  requester_name: 'NGO Helper',
  message: 'Need this for local shelter.',
  ngo_note: 'Verified NGO partner.',
  status: 'pending',
  pickup_scheduled_at: null,
  approved_at: null,
  picked_up_at: null,
  cancelled_at: null,
  created_at: '2026-06-15T10:00:00Z',
  updated_at: '2026-06-15T10:00:00Z',
};

describe('ItemCard', () => {
  it('renders item details correctly', () => {
    render(<ItemCard item={mockItem} />);

    expect(screen.getByText('Warm Winter Coat')).toBeInTheDocument();
    expect(screen.getByText('A warm wool winter coat in excellent condition.')).toBeInTheDocument();
    expect(screen.getByText('Test City')).toBeInTheDocument();
    expect(screen.getByText('Qty: 2')).toBeInTheDocument();
    expect(screen.getByText('like new')).toBeInTheDocument();
    expect(screen.getByText('Available')).toBeInTheDocument();
  });

  it('renders request button when showRequestButton is true and item is available', () => {
    const onRequestClick = jest.fn();
    render(<ItemCard item={mockItem} showRequestButton={true} onRequestClick={onRequestClick} />);

    const button = screen.getByRole('button', { name: /request item/i });
    expect(button).toBeInTheDocument();
    fireEvent.click(button);
    expect(onRequestClick).toHaveBeenCalledWith(42);
  });

  it('does not render request button when item is not available', () => {
    const unavailableItem = { ...mockItem, status: 'reserved' as const };
    render(<ItemCard item={unavailableItem} showRequestButton={true} />);

    expect(screen.queryByRole('button', { name: /request item/i })).not.toBeInTheDocument();
  });

  it('renders edit/remove actions when showEditActions is true', () => {
    const onEditClick = jest.fn();
    const onRemoveClick = jest.fn();
    render(
      <ItemCard
        item={mockItem}
        showEditActions={true}
        onEditClick={onEditClick}
        onRemoveClick={onRemoveClick}
      />
    );

    const editButton = screen.getByRole('button', { name: /edit/i });
    const removeButton = screen.getByRole('button', { name: /remove/i });

    expect(editButton).toBeInTheDocument();
    expect(removeButton).toBeInTheDocument();

    fireEvent.click(editButton);
    expect(onEditClick).toHaveBeenCalledWith(mockItem);

    fireEvent.click(removeButton);
    expect(onRemoveClick).toHaveBeenCalledWith(42);
  });
});

describe('RequestCard', () => {
  it('renders basic request details correctly', () => {
    render(<RequestCard request={mockRequest} currentRole="recipient" />);

    expect(screen.getByText('Warm Winter Coat')).toBeInTheDocument();
    expect(screen.getByText('NGO Helper')).toBeInTheDocument();
    expect(screen.getByText('Jane Doe')).toBeInTheDocument();
    expect(screen.getByText(/Need this for local shelter/)).toBeInTheDocument();
  });

  it('enforces privacy boundary: hides donor phone when status is not approved', () => {
    render(<RequestCard request={mockRequest} currentRole="recipient" />);

    expect(screen.queryByText(/555-1234/)).not.toBeInTheDocument();
    expect(screen.queryByText(/donor contact/i)).not.toBeInTheDocument();
  });

  it('enforces privacy boundary: shows donor phone when status is approved', () => {
    const approvedRequest = { ...mockRequest, status: 'approved' as const };
    render(<RequestCard request={approvedRequest} currentRole="recipient" />);

    expect(screen.getByText(/555-1234/)).toBeInTheDocument();
    expect(screen.getByText(/donor contact/i)).toBeInTheDocument();
  });

  it('shows NGO note to donor and NGO roles', () => {
    const { rerender } = render(<RequestCard request={mockRequest} currentRole="donor" />);
    expect(screen.getByText('Verified NGO partner.')).toBeInTheDocument();

    rerender(<RequestCard request={mockRequest} currentRole="ngo" />);
    expect(screen.getByText('Verified NGO partner.')).toBeInTheDocument();
  });

  it('hides NGO note to recipient role', () => {
    render(<RequestCard request={mockRequest} currentRole="recipient" />);
    expect(screen.queryByText('Verified NGO partner.')).not.toBeInTheDocument();
  });

  it('shows Approve and Reject buttons to donor when pending', () => {
    const onApprove = jest.fn();
    const onReject = jest.fn();
    render(
      <RequestCard
        request={mockRequest}
        currentRole="donor"
        onApprove={onApprove}
        onReject={onReject}
      />
    );

    const approveBtn = screen.getByRole('button', { name: /approve/i });
    const rejectBtn = screen.getByRole('button', { name: /reject/i });

    expect(approveBtn).toBeInTheDocument();
    expect(rejectBtn).toBeInTheDocument();

    fireEvent.click(approveBtn);
    expect(onApprove).toHaveBeenCalledWith(10);

    fireEvent.click(rejectBtn);
    expect(onReject).toHaveBeenCalledWith(10);
  });

  it('shows Confirm Pickup button to donor when approved', () => {
    const onConfirmPickup = jest.fn();
    const approvedRequest = { ...mockRequest, status: 'approved' as const };
    render(
      <RequestCard
        request={approvedRequest}
        currentRole="donor"
        onConfirmPickup={onConfirmPickup}
      />
    );

    const pickupBtn = screen.getByRole('button', { name: /confirm pickup/i });
    expect(pickupBtn).toBeInTheDocument();

    fireEvent.click(pickupBtn);
    expect(onConfirmPickup).toHaveBeenCalledWith(10);
  });

  it('shows Cancel Request to requester when pending', () => {
    const onCancel = jest.fn();
    render(<RequestCard request={mockRequest} currentRole="recipient" onCancel={onCancel} />);

    const cancelBtn = screen.getByRole('button', { name: /cancel request/i });
    expect(cancelBtn).toBeInTheDocument();

    fireEvent.click(cancelBtn);
    expect(onCancel).toHaveBeenCalledWith(10);
  });
});
