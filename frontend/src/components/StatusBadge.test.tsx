import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import { StatusBadge } from './StatusBadge';
import { ItemStatus, RequestStatus } from '@/types';

describe('StatusBadge', () => {
  const testCases: { status: ItemStatus | RequestStatus; expectedText: string; expectedClasses: string }[] = [
    {
      status: 'available',
      expectedText: 'Available',
      expectedClasses: 'bg-emerald-500/10 text-emerald-400 border-emerald-400/20',
    },
    {
      status: 'reserved',
      expectedText: 'Reserved',
      expectedClasses: 'bg-amber-500/10 text-amber-400 border-amber-400/20',
    },
    {
      status: 'donated',
      expectedText: 'Donated',
      expectedClasses: 'bg-lime-500/10 text-lime-400 border-lime-400/20',
    },
    {
      status: 'removed',
      expectedText: 'Removed',
      expectedClasses: 'bg-rose-500/10 text-rose-400 border-rose-400/20',
    },
    {
      status: 'pending',
      expectedText: 'Pending',
      expectedClasses: 'bg-slate-500/10 text-slate-400 border-slate-400/20',
    },
    {
      status: 'approved',
      expectedText: 'Approved',
      expectedClasses: 'bg-sky-500/10 text-sky-400 border-sky-400/20',
    },
    {
      status: 'rejected',
      expectedText: 'Rejected',
      expectedClasses: 'bg-rose-500/10 text-rose-400 border-rose-400/20',
    },
    {
      status: 'picked_up',
      expectedText: 'Picked Up',
      expectedClasses: 'bg-lime-500/10 text-lime-400 border-lime-400/20',
    },
    {
      status: 'cancelled',
      expectedText: 'Cancelled',
      expectedClasses: 'bg-rose-500/10 text-rose-400 border-rose-400/20',
    },
  ];

  testCases.forEach(({ status, expectedText, expectedClasses }) => {
    it(`renders correct text and classes for status "${status}"`, () => {
      render(<StatusBadge status={status} />);
      const badge = screen.getByText(expectedText);
      expect(badge).toBeInTheDocument();
      
      const classes = expectedClasses.split(' ');
      classes.forEach((cls) => {
        expect(badge).toHaveClass(cls);
      });
    });
  });
});
