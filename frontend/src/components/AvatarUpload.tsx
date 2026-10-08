'use client';

import { useEffect, useRef, useState } from 'react';
import api from '@/lib/axios';

interface AvatarUploadProps {
  photoUrl: string | null;
  fallbackLabel: string;
  uploading: boolean;
  onUpload: (file: File) => Promise<void>;
  onRemove: () => Promise<void>;
}

const MAX_SIZE_MB = 5;
const ACCEPT = 'image/jpeg,image/png,image/webp';

export default function AvatarUpload({ photoUrl, fallbackLabel, uploading, onUpload, onRemove }: AvatarUploadProps) {
  const [preview, setPreview] = useState<string | null>(null);
  const [prevPhotoUrl, setPrevPhotoUrl] = useState(photoUrl);
  const [error, setError] = useState('');
  const [removing, setRemoving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  // Clear stale preview when the photo is removed (render-phase adjustment).
  if (photoUrl !== prevPhotoUrl) {
    setPrevPhotoUrl(photoUrl);
    setPreview(null);
  }

  // Fetch the protected photo as a blob (JWT is attached by the axios interceptor).
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

  const initials = (fallbackLabel || '?')
    .split(' ')
    .map((p) => p[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();

  const handleSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      setError('Only JPG, PNG or WebP images are allowed.');
      return;
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      setError(`Image must be under ${MAX_SIZE_MB}MB.`);
      return;
    }
    setError('');
    await onUpload(file);
  };

  const handleRemove = async () => {
    setRemoving(true);
    try {
      await onRemove();
    } finally {
      setRemoving(false);
    }
  };

  return (
    <div className="flex items-center gap-5">
      <div className="relative shrink-0">
        <div className="w-24 h-24 rounded-full overflow-hidden bg-[#12b388]/10 border border-gray-100 flex items-center justify-center">
          {preview ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={preview} alt="Profile photo" className="w-full h-full object-cover" />
          ) : (
            <span className="text-2xl font-bold text-[#12b388]">{initials}</span>
          )}
        </div>
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          aria-label="Change profile photo"
          className="absolute bottom-0 right-0 w-8 h-8 rounded-full bg-black text-white text-sm flex items-center justify-center hover:bg-gray-800 transition-colors disabled:opacity-50"
        >
          {uploading ? '…' : '📷'}
        </button>
      </div>
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
            className="px-5 py-2 rounded-full bg-black text-white text-sm font-bold hover:bg-gray-800 transition-colors disabled:opacity-50"
          >
            {uploading ? 'Uploading...' : photoUrl ? 'Change photo' : 'Upload photo'}
          </button>
          {photoUrl && (
            <button
              type="button"
              onClick={handleRemove}
              disabled={uploading || removing}
              className="px-5 py-2 rounded-full border border-gray-200 text-sm font-bold text-gray-600 hover:bg-gray-50 transition-colors disabled:opacity-50"
            >
              {removing ? 'Removing...' : 'Remove'}
            </button>
          )}
        </div>
        <p className="text-xs text-gray-400">JPG, PNG or WebP · max {MAX_SIZE_MB}MB</p>
        {error && <p className="text-xs font-medium text-red-500">{error}</p>}
        <input ref={inputRef} type="file" accept={ACCEPT} className="hidden" onChange={handleSelect} />
      </div>
    </div>
  );
}
