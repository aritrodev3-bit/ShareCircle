import { ItemOut } from '@/types';
import { StatusBadge, CategoryBadge } from './StatusBadge';
import { MapPin, Calendar, Layers, Activity } from 'lucide-react';

interface ItemCardProps {
  item: ItemOut;
  showRequestButton?: boolean;
  showEditActions?: boolean;
  onRequestClick?: (itemId: number) => void;
  onEditClick?: (item: ItemOut) => void;
  onRemoveClick?: (itemId: number) => void;
}

export default function ItemCard({
  item,
  showRequestButton = false,
  showEditActions = false,
  onRequestClick,
  onEditClick,
  onRemoveClick,
}: ItemCardProps) {
  const formattedDate = new Date(item.created_at).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });

  return (
    <div className="bg-surface-1 border border-[rgba(167,209,41,0.08)] rounded-[14px] p-4 flex flex-col justify-between transition-all duration-150 hover:bg-surface-2 group">
      <div>
        {/* Image if available */}
        {item.image_url && (
          <div className="w-full h-40 rounded-lg overflow-hidden mb-3 bg-bg-secondary relative">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={item.image_url}
              alt={item.title}
              className="w-full h-full object-cover opacity-90 group-hover:opacity-100 transition-opacity duration-150"
              onError={(e) => {
                // Hide broken images
                (e.target as HTMLElement).style.display = 'none';
              }}
            />
          </div>
        )}

        {/* Title & Status */}
        <div className="flex justify-between items-start mb-2 gap-2">
          <h3 className="font-serif text-base font-medium text-text-primary leading-snug">
            {item.title}
          </h3>
          <div className="flex flex-col items-end gap-1.5 shrink-0">
            <StatusBadge status={item.status} />
            {(item as any).score !== undefined && (
              <span className="bg-info/15 text-info border border-info/20 text-[10px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap">
                Match: {Math.round((item as any).score * 100)}%
              </span>
            )}
          </div>
        </div>

        {/* Category Badge */}
        <div className="mb-3">
          <CategoryBadge category={item.category} />
        </div>

        {/* Description */}
        <p className="text-sm text-text-secondary mb-4 line-clamp-3">
          {item.description}
        </p>

        {/* Metadata Grid */}
        <div className="grid grid-cols-2 gap-y-2 gap-x-4 text-xs text-text-muted mb-4 border-t border-[rgba(167,209,41,0.04)] pt-3">
          <div className="flex items-center space-x-1.5">
            <MapPin className="h-3.5 w-3.5 text-olive-500" />
            <span className="truncate">{item.city}</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <Activity className="h-3.5 w-3.5 text-olive-500" />
            <span className="capitalize">{item.condition.replace('_', ' ')}</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <Layers className="h-3.5 w-3.5 text-olive-500" />
            <span>Qty: {item.quantity}</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <Calendar className="h-3.5 w-3.5 text-olive-500" />
            <span>{formattedDate}</span>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="mt-2 pt-2 border-t border-[rgba(167,209,41,0.04)]">
        {showRequestButton && item.status === 'available' && onRequestClick && (
          <button
            onClick={() => onRequestClick(item.id)}
            className="w-full bg-lime-500 hover:bg-lime-700 text-bg-primary py-2 px-4 rounded-lg text-sm transition-all duration-150 focus-ring cursor-pointer"
          >
            Request item
          </button>
        )}

        {showEditActions && (
          <div className="flex gap-2">
            {onEditClick && item.status !== 'donated' && item.status !== 'removed' && (
              <button
                onClick={() => onEditClick(item)}
                className="flex-1 bg-transparent text-lime-400 border border-olive-500 hover:bg-surface-hover py-2 px-3 rounded-lg text-xs transition-all duration-150 focus-ring cursor-pointer"
              >
                Edit
              </button>
            )}
            {onRemoveClick && item.status !== 'removed' && item.status !== 'donated' && (
              <button
                onClick={() => onRemoveClick(item.id)}
                className="flex-1 bg-transparent text-error border border-error/20 hover:bg-error/5 py-2 px-3 rounded-lg text-xs transition-all duration-150 focus-ring cursor-pointer"
              >
                Remove
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
