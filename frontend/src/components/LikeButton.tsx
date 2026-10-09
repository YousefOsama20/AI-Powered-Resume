'use client';

import { useEffect, useState } from 'react';
import { Heart } from 'lucide-react';
import api from '@/lib/axios';

type Props = {
  jd_id: string;
  initialLiked?: boolean;
  size?: number;
  onToggle?: (liked: boolean) => void;
};

/** Heart toggle backed by POST/DELETE /ats/jobs/{jd_id}/like. Optimistic UI. */
export default function LikeButton({ jd_id, initialLiked = false, size = 18, onToggle }: Props) {
  const [liked, setLiked] = useState(initialLiked);
  const [busy, setBusy] = useState(false);

  // Sync when the parent loads the initial value asynchronously
  // (e.g. job detail page fetches liked ids after mount).
  useEffect(() => {
    setLiked(initialLiked);
  }, [initialLiked, jd_id]);

  const toggle = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (busy) return;
    const next = !liked;
    setLiked(next); // optimistic
    setBusy(true);
    try {
      if (next) await api.post(`/ats/jobs/${jd_id}/like`);
      else await api.delete(`/ats/jobs/${jd_id}/like`);
      onToggle?.(next);
    } catch (err) {
      console.error(err);
      setLiked(!next); // revert
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      type="button"
      onClick={toggle}
      disabled={busy}
      aria-pressed={liked}
      title={liked ? 'Unlike this job' : 'Like this job'}
      className={`inline-flex items-center justify-center rounded-full p-2 transition-colors disabled:opacity-50 ${
        liked ? 'text-red-500 hover:bg-red-50' : 'text-gray-400 hover:text-red-500 hover:bg-red-50'
      }`}
    >
      <Heart size={size} fill={liked ? 'currentColor' : 'none'} />
    </button>
  );
}
