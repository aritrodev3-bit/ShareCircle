import { RequestOut, UserRole } from '@/types';
import { StatusBadge } from './StatusBadge';
import { Phone, Calendar, User, MessageSquare, AlertCircle, MapPin, ExternalLink, Navigation } from 'lucide-react';

interface RequestCardProps {
  request: RequestOut;
  currentRole: UserRole;
  onApprove?: (reqId: number) => void;
  onReject?: (reqId: number) => void;
  onConfirmPickup?: (reqId: number) => void;
  onCancel?: (reqId: number) => void;
}

export default function RequestCard({
  request,
  currentRole,
  onApprove,
  onReject,
  onConfirmPickup,
  onCancel,
}: RequestCardProps) {
  const formattedDate = new Date(request.created_at).toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });

  const isApproved = request.status === 'approved';
  const isPending = request.status === 'pending';

  return (
    <div className="bg-surface-1 border border-[rgba(167,209,41,0.08)] rounded-[14px] p-4 flex flex-col justify-between transition-all duration-150 hover:bg-surface-2">
      <div>
        {/* Item Title & Status */}
        <div className="flex justify-between items-start mb-3 gap-2">
          <h3 className="font-serif text-base font-medium text-text-primary leading-snug">
            {request.item_title}
          </h3>
          <StatusBadge status={request.status} />
        </div>

        {/* Roles Details */}
        <div className="space-y-2 text-sm text-text-secondary mb-3 pt-2 border-t border-[rgba(167,209,41,0.04)]">
          <div className="flex items-center space-x-2">
            <User className="h-4 w-4 text-olive-500" />
            <span>
              <strong>Donor:</strong> {request.donor_name}
            </span>
          </div>

          <div className="flex items-center space-x-2">
            <User className="h-4 w-4 text-olive-500" />
            <span>
              <strong>Requester:</strong> {request.requester_name}
            </span>
          </div>
        </div>

        {/* Message */}
        {request.message && (
          <div className="bg-bg-secondary p-2.5 rounded-lg mb-3 flex items-start space-x-2 border border-[rgba(167,209,41,0.04)]">
            <MessageSquare className="h-4 w-4 text-olive-500 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-text-secondary italic">
              &ldquo;{request.message}&rdquo;
            </p>
          </div>
        )}

        {/* NGO Note - visible to donor and NGO */}
        {request.ngo_note && (currentRole === 'donor' || currentRole === 'ngo') && (
          <div className="bg-bg-secondary p-2.5 rounded-lg mb-3 flex items-start space-x-2 border-l-2 border-info border-y border-r border-[rgba(167,209,41,0.04)]">
            <AlertCircle className="h-4 w-4 text-info mt-0.5 flex-shrink-0" />
            <div>
              <span className="text-[10px] text-info font-medium uppercase tracking-wider block">
                NGO note
              </span>
              <p className="text-xs text-text-secondary">{request.ngo_note}</p>
            </div>
          </div>
        )}

        {/* Privacy-Safe Contact Info */}
        {isApproved && request.donor_phone && (
          <div className="bg-[rgba(167,209,41,0.06)] p-3 rounded-lg border border-[rgba(167,209,41,0.16)] mb-3 flex items-center space-x-2 text-lime-400">
            <Phone className="h-4 w-4 animate-pulse" />
            <span className="text-sm font-medium">
              Donor contact: <span className="text-text-primary select-all">{request.donor_phone}</span>
            </span>
          </div>
        )}

        {/* Location Info (if approved) */}
        {isApproved && (request.item_city || request.item_pincode || request.pickup_location) && (
          <div className="bg-bg-secondary p-3 rounded-lg border border-[rgba(167,209,41,0.04)] mb-3 space-y-3">
            {/* Listing Location */}
            {(request.item_city || request.item_pincode) && (
              <div className="flex items-start space-x-2">
                <MapPin className="h-4 w-4 text-lime-400 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider block">
                    Listing Location
                  </span>
                  <p className="text-xs text-text-secondary font-medium">
                    {request.item_city || 'N/A'}{request.item_pincode ? `, ${request.item_pincode}` : ''}
                  </p>
                  {request.item_lat !== null && request.item_lng !== null && (
                    <a
                      href={`https://www.google.com/maps/search/?api=1&query=${request.item_lat},${request.item_lng}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center space-x-1 text-[11px] text-lime-400 hover:text-lime-300 mt-1 transition-colors font-medium hover:underline"
                    >
                      <span>View on Google Maps</span>
                      <ExternalLink className="h-3 w-3" />
                    </a>
                  )}
                </div>
              </div>
            )}

            {/* Drop-off / Pickup Instructions */}
            <div className="flex items-start space-x-2 pt-2.5 border-t border-[rgba(167,209,41,0.06)]">
              <Navigation className="h-4 w-4 text-lime-400 mt-0.5 flex-shrink-0" />
              <div>
                <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider block">
                  Drop-off / Pickup Instructions
                </span>
                <p className="text-xs text-text-secondary mt-0.5 whitespace-pre-line leading-relaxed">
                  {request.pickup_location || 'Pickup Location: Use listing location above'}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Request Date */}
        <div className="flex items-center space-x-1 text-xs text-text-muted mt-2">
          <Calendar className="h-3.5 w-3.5" />
          <span>Requested on {formattedDate}</span>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="mt-4 pt-3 border-t border-[rgba(167,209,41,0.04)] flex gap-2">
        {/* Donor Actions */}
        {currentRole === 'donor' && isPending && onApprove && onReject && (
          <>
            <button
              onClick={() => onApprove(request.id)}
              className="flex-1 bg-lime-500 hover:bg-lime-700 text-bg-primary py-2 px-3 rounded-lg text-xs font-medium transition-all duration-150 focus-ring cursor-pointer"
            >
              Approve
            </button>
            <button
              onClick={() => onReject(request.id)}
              className="flex-1 bg-transparent text-error border border-error/20 hover:bg-error/5 py-2 px-3 rounded-lg text-xs font-medium transition-all duration-150 focus-ring cursor-pointer"
            >
              Reject
            </button>
          </>
        )}

        {currentRole === 'donor' && isApproved && onConfirmPickup && (
          <button
            onClick={() => onConfirmPickup(request.id)}
            className="w-full bg-lime-500 hover:bg-lime-700 text-bg-primary py-2 px-4 rounded-lg text-sm font-medium transition-all duration-150 focus-ring cursor-pointer"
          >
            Confirm pickup
          </button>
        )}

        {/* Requester Actions */}
        {(currentRole === 'recipient' || currentRole === 'ngo') && isPending && onCancel && (
          <button
            onClick={() => onCancel(request.id)}
            className="w-full bg-transparent text-error border border-error/20 hover:bg-error/5 py-2 px-4 rounded-lg text-sm font-medium transition-all duration-150 focus-ring cursor-pointer"
          >
            Cancel request
          </button>
        )}
      </div>
    </div>
  );
}
