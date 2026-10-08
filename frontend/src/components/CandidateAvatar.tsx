'use client';

import { useEffect, useState } from 'react';
import api from '@/lib/axios';

interface CandidateAvatarProps {
  photoUrl?: string | null;
  name?: string | null;
  size?: number;
}

// Company-side avatar: blob-fetches the JWT-protected photo, falls back to initials.
export default function CandidateAvatar({ photoUrl, name, size = 52 }: CandidateAvatarProps) {
  const [preview, setPreview] = useState<string | null>(null);
  const [prevUrl, setPrevUrl] = useState<string | null>(photoUrl ?? null);

  // Clear stale preview when the URL changes/removes (render-phase adjustment).
  if ((photoUrl ?? null) !== prevUrl) {
    setPrevUrl(photoUrl ?? null);
    setPreview(null);
  }

  useEffect(() => {
    if (!photoUrl) return;
    let active = true;
    let objectUrl: string | null = null;
    api
      .get(photoUrl, { responseType: 'blob' })
      .then((res) => {
        if (!active) return;
        objectUrl = URL.createObjectURL(res.data);
        setPreview(objectUrl);
      })
      .catch(() => {
        if (active) setPreview(null);
      });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [photoUrl]);

  const initials = (name || '?')
    .split(' ')
    .map((p) => p[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();

  const style = { width: size, height: size };

  if (preview) {
    return (
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={preview}
        alt={name || 'Candidate photo'}
        style={style}
        className="rounded-full object-cover shrink-0 bg-gray-100"
      />
    );
  }

  return (
    <div
      style={style}
      className="rounded-full bg-[#12b388]/10 text-[#12b388] font-bold flex items-center justify-center shrink-0 text-lg"
    >
      {initials}
    </div>
  );
}
