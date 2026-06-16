import { ItemStatus, RequestStatus, ItemCategory } from '@/types';

interface StatusBadgeProps {
  status: ItemStatus | RequestStatus;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const config: Record<
    ItemStatus | RequestStatus,
    { className: string; label: string }
  > = {
    available: {
      className: 'bg-emerald-500/10 text-emerald-400 border-emerald-400/20',
      label: 'Available',
    },
    reserved: {
      className: 'bg-amber-500/10 text-amber-400 border-amber-400/20',
      label: 'Reserved',
    },
    donated: {
      className: 'bg-lime-500/10 text-lime-400 border-lime-400/20',
      label: 'Donated',
    },
    removed: {
      className: 'bg-rose-500/10 text-rose-400 border-rose-400/20',
      label: 'Removed',
    },
    pending: {
      className: 'bg-slate-500/10 text-slate-400 border-slate-400/20',
      label: 'Pending',
    },
    approved: {
      className: 'bg-sky-500/10 text-sky-400 border-sky-400/20',
      label: 'Approved',
    },
    rejected: {
      className: 'bg-rose-500/10 text-rose-400 border-rose-400/20',
      label: 'Rejected',
    },
    picked_up: {
      className: 'bg-lime-500/10 text-lime-400 border-lime-400/20',
      label: 'Picked Up',
    },
    cancelled: {
      className: 'bg-rose-500/10 text-rose-400 border-rose-400/20',
      label: 'Cancelled',
    },
  };

  const current = config[status] || {
    className: 'bg-slate-500/10 text-slate-400 border-slate-400/20',
    label: status,
  };

  return (
    <span className={`inline-flex items-center rounded-[6px] px-2.5 py-0.5 text-xs font-medium border ${current.className}`}>
      {current.label}
    </span>
  );
}

interface CategoryBadgeProps {
  category: ItemCategory;
}

export function CategoryBadge({ category }: CategoryBadgeProps) {
  const label = category.replace('_', ' ');
  return (
    <span className="inline-flex items-center rounded-[6px] px-2 py-0.5 text-[11px] font-medium border bg-olive-500/30 text-lime-400 border-lime-400/20">
      {label.charAt(0).toUpperCase() + label.slice(1)}
    </span>
  );
}

