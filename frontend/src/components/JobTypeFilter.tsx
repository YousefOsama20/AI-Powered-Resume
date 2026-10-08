'use client';

import { useEffect, useState } from 'react';
import api from '@/lib/axios';

export type JobTaxonomy = { id: string; name: string };

type Props = {
  selected: string[];
  onChange: (ids: string[]) => void;
  allLabel?: string;
};

/** Build a repeat-param query string the backend understands:
 *  ?job_type_id=A&job_type_id=B (multi-select). */
export function buildJobTypeQuery(selected: string[], base: Record<string, string | number> = {}) {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries(base)) params.set(k, String(v));
  for (const id of selected) params.append('job_type_id', id);
  const s = params.toString();
  return s ? `?${s}` : '';
}

/** Client-side fallback: keep jobs whose type id OR name matches selection. */
export function filterJobsByType<T extends { job_type?: { id?: string; name?: string } | null }>(
  jobs: T[],
  selected: string[],
  idToName?: Map<string, string>,
): T[] {
  if (!selected.length) return jobs;
  const sel = new Set(selected.map(s => s.toLowerCase()));
  return jobs.filter((j) => {
    const tid = (j.job_type?.id || '').toLowerCase();
    const tname = (j.job_type?.name || '').toLowerCase();
    if (tid && sel.has(tid)) return true;
    if (tname) {
      if (sel.has(tname)) return true;
      // Match by id→name mapping in case caller filters by id but payload only has names.
      if (idToName) {
        for (const id of sel) {
          const mapped = (idToName.get(id) || idToName.get(id.toLowerCase()) || '').toLowerCase();
          if (mapped && mapped === tname) return true;
        }
      }
    }
    return false;
  });
}

export default function JobTypeFilter({ selected, onChange, allLabel = 'All Jobs' }: Props) {
  const [types, setTypes] = useState<JobTaxonomy[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    api
      .get('/profile/taxonomy')
      .then((res) => {
        if (!alive) return;
        setTypes(res.data?.job_types || []);
        setLoading(false);
      })
      .catch(() => {
        if (!alive) return;
        setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  const toggle = (id: string) => {
    if (selected.includes(id)) onChange(selected.filter((s) => s !== id));
    else onChange([...selected, id]);
  };

  const pill = (active: boolean) =>
    `px-4 py-1.5 rounded-full text-xs font-medium cursor-pointer transition-colors border ${
      active
        ? 'bg-gray-900 text-white border-gray-900'
        : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50'
    }`;

  if (loading) {
    return (
      <div className="flex gap-2 mb-8 flex-wrap" aria-label="Loading job type filters">
        {[0, 1, 2, 3].map((i) => (
          <span key={i} className="px-8 py-3 bg-gray-100 rounded-full animate-pulse" />
        ))}
      </div>
    );
  }

  if (!types.length) return null;

  const allActive = selected.length === 0;

  return (
    <div className="flex gap-2 mb-8 flex-wrap" role="group" aria-label="Filter jobs by type">
      <button type="button" onClick={() => onChange([])} className={pill(allActive)}>
        {allLabel}
        {!allActive && <span className="ml-1 opacity-60">({selected.length} selected)</span>}
      </button>
      {types.map((t) => {
        const active = selected.includes(t.id);
        return (
          <button
            key={t.id}
            type="button"
            onClick={() => toggle(t.id)}
            aria-pressed={active}
            title={active ? `Remove ${t.name} filter` : `Filter by ${t.name}`}
            className={pill(active)}
          >
            {active ? `✓ ${t.name}` : t.name}
          </button>
        );
      })}
      {!allActive && (
        <button
          type="button"
          onClick={() => onChange([])}
          className="px-4 py-1.5 rounded-full text-xs font-bold text-gray-400 hover:text-gray-700 underline underline-offset-2"
        >
          Clear
        </button>
      )}
    </div>
  );
}
