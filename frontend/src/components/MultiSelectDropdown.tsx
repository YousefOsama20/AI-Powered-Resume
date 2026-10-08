'use client';

import { useState, useRef, useEffect } from 'react';

interface Option {
  id: string;
  name: string;
}

interface MultiSelectDropdownProps {
  options: Option[];
  selected: string[];
  onToggle: (id: string) => void;
  onClear?: () => void;
  placeholder?: string;
}

export default function MultiSelectDropdown({
  options,
  selected,
  onToggle,
  onClear,
  placeholder = 'Please select',
}: MultiSelectDropdownProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const selectedNames = options
    .filter((o) => selected.includes(o.id))
    .map((o) => o.name);

  const buttonLabel =
    selected.length === 0
      ? placeholder
      : `${selected.length} selected — ${selectedNames.slice(0, 3).join(', ')}${
          selectedNames.length > 3 ? '...' : ''
        }`;

  return (
    <div ref={ref} className="relative w-full">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full bg-gray-50 border-none rounded-lg p-4 text-gray-900 focus:ring-2 focus:ring-[#12b388] outline-none flex items-center justify-between gap-3 text-left"
      >
        <span
          className={`truncate text-sm sm:text-base ${
            selected.length === 0 ? 'text-gray-400' : 'text-gray-900 font-medium'
          }`}
        >
          {buttonLabel}
        </span>
        <span className="flex items-center gap-2 shrink-0">
          {selected.length > 0 && (
            <span className="text-xs font-bold bg-[#12b388] text-white rounded-full px-2.5 py-0.5">
              {selected.length}
            </span>
          )}
          <svg
            className={`w-5 h-5 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
          </svg>
        </span>
      </button>

      {open && (
        <div className="absolute z-20 mt-2 w-full bg-white border border-gray-100 rounded-xl shadow-lg overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2 border-b border-gray-100">
            <span className="text-xs font-medium text-gray-500">
              {selected.length} selected (unlimited)
            </span>
            {selected.length > 0 && (
              <button
                type="button"
                onClick={() => onClear?.()}
                className="text-xs font-bold text-gray-400 hover:text-red-500 transition-colors"
              >
                Clear all
              </button>
            )}
          </div>
          <div className="max-h-60 overflow-y-auto p-2 space-y-1">
            {options.length === 0 && (
              <p className="text-sm text-gray-400 px-3 py-4 text-center">No options available</p>
            )}
            {options.map((opt) => {
              const active = selected.includes(opt.id);
              return (
                <button
                  key={opt.id}
                  type="button"
                  onClick={() => onToggle(opt.id)}
                  className={`w-full flex items-center gap-3 p-3 rounded-lg text-sm font-medium transition-colors text-left ${
                    active ? 'bg-[#12b388]/10 text-[#12b388]' : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <div
                    className={`w-5 h-5 rounded flex items-center justify-center shrink-0 ${
                      active ? 'bg-[#12b388] text-white' : 'bg-gray-200'
                    }`}
                  >
                    {active && '✓'}
                  </div>
                  <span className="truncate">{opt.name}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
