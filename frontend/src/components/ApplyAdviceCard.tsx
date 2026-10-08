'use client';

import { useState } from 'react';
import api from '@/lib/axios';

type Advice = {
  verdict: 'APPLY' | 'MAYBE' | 'SKIP';
  score_0_100: number;
  reason: string;
  strengths: string[];
  gaps: string[];
  two_week_plan: string[];
  interview_tips: string[];
};

const verdictStyle = (v: string) => {
  if (v === 'APPLY') return 'bg-[#12b388]/10 text-[#12b388] ring-1 ring-[#12b388]/30';
  if (v === 'MAYBE') return 'bg-amber-100 text-amber-700 ring-1 ring-amber-200';
  return 'bg-gray-100 text-gray-600 ring-1 ring-gray-200';
};

export default function ApplyAdviceCard({ jd_id }: { jd_id: string }) {
  const [advice, setAdvice] = useState<Advice | null>(null);
  const [cached, setCached] = useState(false);
  const [cachedAt, setCachedAt] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAdvice = async (force = false) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.get(`/ats/jobs/${jd_id}/apply-advice${force ? '?force=1' : ''}`);
      setAdvice(res.data.advice);
      setCached(!!res.data.cached);
      setCachedAt(res.data.created_at || null);
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number; data?: { message?: string } } })?.response?.status;
      const message = (err as { response?: { data?: { message?: string } } })?.response?.data?.message;
      if (status === 503) {
        setError('AI advice unavailable — the LLM is not configured. Contact your admin.');
      } else if (status === 400) {
        setError(message || 'Upload a CV first to get AI advice.');
      } else {
        setError(message || 'Failed to get AI advice. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-2xl border border-gray-100 p-6">
      <div className="flex items-center justify-between gap-4 border-b border-gray-100 pb-4">
        <h3 className="text-lg font-bold text-gray-900">🤖 AI Apply Advisor</h3>
        <div className="flex items-center gap-2 shrink-0">
          {advice && (
            <button
              onClick={() => fetchAdvice(true)}
              disabled={loading}
              className="px-4 py-1.5 text-xs font-bold text-gray-600 bg-gray-100 rounded-full hover:bg-gray-200 transition-colors disabled:opacity-50"
            >
              Refresh ⟳
            </button>
          )}
          <button
            onClick={() => fetchAdvice(false)}
            disabled={loading}
            className="px-5 py-2 bg-black text-white text-xs font-bold rounded-full hover:bg-gray-800 transition-colors disabled:opacity-50"
          >
            {loading ? 'Asking AI...' : advice ? 'Ask again' : 'Ask AI: Should I apply?'}
          </button>
        </div>
      </div>

      {loading && (
        <div className="mt-4 space-y-3 animate-pulse">
          <div className="h-6 bg-gray-100 rounded-full w-1/3" />
          <div className="h-4 bg-gray-100 rounded w-full" />
          <div className="h-4 bg-gray-100 rounded w-5/6" />
        </div>
      )}

      {!loading && error && (
        <p className="mt-4 text-sm font-medium text-amber-700 bg-amber-50 border border-amber-100 rounded-xl p-4">{error}</p>
      )}

      {!loading && !error && !advice && (
        <p className="mt-4 text-sm text-gray-500">
          Get a personalized verdict based on your CV vs this job — matched skills, gaps, and a 2-week plan to close them.
        </p>
      )}

      {!loading && advice && (
        <div className="mt-4 space-y-5">
          <div className="flex items-center gap-3 flex-wrap">
            <span className={`px-4 py-1.5 rounded-full text-sm font-bold ${verdictStyle(advice.verdict)}`}>
              {advice.verdict === 'APPLY' ? '✓ APPLY' : advice.verdict === 'MAYBE' ? '◐ MAYBE' : '✕ SKIP'}
            </span>
            <span className="text-sm font-bold text-gray-700">{advice.score_0_100 ?? 0}/100 fit</span>
            {cached && <span className="text-xs text-gray-400">Cached{cachedAt ? ` • ${new Date(cachedAt).toLocaleDateString()}` : ''}</span>}
          </div>

          <p className="text-sm text-gray-700 leading-relaxed">{advice.reason}</p>

          {(advice.strengths?.length > 0) && (
            <div>
              <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Your strengths</p>
              <div className="flex flex-wrap gap-2">
                {advice.strengths.map(s => (
                  <span key={`st-${s}`} className="px-3 py-1 text-xs font-medium rounded-full bg-[#12b388]/10 text-[#12b388]">✓ {s}</span>
                ))}
              </div>
            </div>
          )}

          {(advice.gaps?.length > 0) && (
            <div>
              <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Gaps to close</p>
              <div className="flex flex-wrap gap-2">
                {advice.gaps.map(s => (
                  <span key={`gp-${s}`} className="px-3 py-1 text-xs font-medium rounded-full bg-red-50 text-red-500">✗ {s}</span>
                ))}
              </div>
            </div>
          )}

          {(advice.two_week_plan?.length > 0) && (
            <div>
              <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">2-week plan</p>
              <ol className="space-y-2">
                {advice.two_week_plan.map((step, i) => (
                  <li key={`pl-${i}`} className="flex gap-3 text-sm text-gray-700">
                    <span className="w-6 h-6 rounded-full bg-black text-white text-xs font-bold flex items-center justify-center shrink-0">{i + 1}</span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {(advice.interview_tips?.length > 0) && (
            <div>
              <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Interview tips</p>
              <ul className="space-y-1.5">
                {advice.interview_tips.map((tip, i) => (
                  <li key={`tp-${i}`} className="text-sm text-gray-600">💡 {tip}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
