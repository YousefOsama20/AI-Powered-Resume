'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import DashboardLayout from '@/components/DashboardLayout';
import ApplyAdviceCard from '@/components/ApplyAdviceCard';
import api from '@/lib/axios';
import { MapPin, Briefcase, Building2, Globe, ArrowLeft } from 'lucide-react';

export default function JobDetailClient({ jd_id }: { jd_id: string }) {
  const [job, setJob] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [applying, setApplying] = useState(false);
  const [applied, setApplied] = useState(false);
  const [logoError, setLogoError] = useState(false);

  // Normalize API skills: backend returns arrays, but be tolerant of
  // comma-strings, null, or legacy shapes so the split never silently hides.
  const normalizeSkills = (value: any): string[] => {
    if (Array.isArray(value)) {
      const seen = new Set<string>();
      const out: string[] = [];
      for (const s of value) {
        if (typeof s === 'string') {
          const v = s.trim().toLowerCase();
          if (v && !seen.has(v)) {
            seen.add(v);
            out.push(v);
          }
        }
      }
      return out;
    }
    if (typeof value === 'string') {
      const text = value.trim();
      if (!text) return [];
      // Tolerate legacy JSON-encoded lists: '["python", "sql"]'
      if (text.startsWith('[')) {
        try {
          const parsed = JSON.parse(text);
          if (Array.isArray(parsed)) return normalizeSkills(parsed);
        } catch {
          // fall through to comma-split
        }
      }
      return normalizeSkills(text.split(','));
    }
    return [];
  };

  // Last-resort client split: divide the raw description on
  // "nice to have / preferred / bonus / a plus" markers so customers still
  // see an Essential vs Nice-to-have division when stored skills are empty.
  const splitDescriptionFallback = (desc: string): { essentialText: string; electiveText: string } => {
    if (!desc) return { essentialText: '', electiveText: '' };
    const m = desc.search(/nice\s*to\s*have|nice-to-have|preferred|bonus|\ba\s+plus\b|desirable|beneficial|\boptional\b|would\s+be\s+a\s+plus|is\s+a\s+plus|is\s+preferred/i);
    if (m === -1) return { essentialText: desc, electiveText: '' };
    return { essentialText: desc.slice(0, m).trim(), electiveText: desc.slice(m).trim() };
  };

  useEffect(() => {
    api.get(`/ats/jobs/public/${jd_id}`)
      .then(res => {
        setJob(res.data);
        setLogoError(false);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, [jd_id]);

  const handleApply = async () => {
    setApplying(true);
    try {
      await api.post(`/ats/jobs/${jd_id}/apply`);
      setApplied(true);
    } catch (err: any) {
      alert(err?.response?.data?.message || 'Failed to apply or already applied.');
    }
    setApplying(false);
  };

  if (loading) {
    return (
      <DashboardLayout role="CANDIDATE">
        <div className="max-w-3xl space-y-6 animate-pulse">
          <div className="bg-white h-48 rounded-2xl border border-gray-100" />
          <div className="bg-white h-64 rounded-2xl border border-gray-100" />
        </div>
      </DashboardLayout>
    );
  }

  if (!job) {
    return (
      <DashboardLayout role="CANDIDATE">
        <div className="max-w-3xl bg-white rounded-2xl border border-gray-100 p-12 text-center">
          <h3 className="text-xl font-bold text-gray-900 mb-2">Job not found</h3>
          <p className="text-gray-500 mb-6">This job posting may have been removed or is no longer public.</p>
          <Link href="/candidate/dashboard" className="px-6 py-2.5 bg-black text-white font-bold rounded-full hover:bg-gray-800 transition-colors">
            Back to Jobs
          </Link>
        </div>
      </DashboardLayout>
    );
  }

  const company = job.company || {};
  const essentialSkills = normalizeSkills(job.essential_skills);
  const electiveSkills = normalizeSkills(job.elective_skills).filter(s => !essentialSkills.includes(s));
  const matchedEss: string[] = normalizeSkills(job.matched_essential_skills);
  const missingEss: string[] = normalizeSkills(job.missing_essential_skills);
  const matchedEle: string[] = normalizeSkills(job.matched_elective_skills);
  const hasOverlap = matchedEss.length > 0 || matchedEle.length > 0 || missingEss.length > 0;
  const hasStructuredSkills = essentialSkills.length > 0 || electiveSkills.length > 0;
  const descFallback = !hasStructuredSkills ? splitDescriptionFallback(job.job_description || '') : { essentialText: '', electiveText: '' };
  const skillChip = (s: string, kind: 'ess' | 'ele') => {
    const isMatched = kind === 'ess' ? matchedEss.includes(s) : matchedEle.includes(s);
    const isMissing = kind === 'ess' ? (missingEss.includes(s) || (hasOverlap && !matchedEss.includes(s))) : false;
    if (isMatched) return 'bg-[#12b388]/10 text-[#12b388] ring-1 ring-[#12b388]/30';
    if (isMissing && kind === 'ess') return 'bg-red-50 text-red-500 ring-1 ring-red-100';
    return kind === 'ess' ? 'bg-[#12b388]/10 text-[#12b388]' : 'bg-gray-100 text-gray-700';
  };

  return (
    <DashboardLayout role="CANDIDATE">
      <div className="max-w-3xl space-y-6">
        <Link href="/candidate/dashboard" className="inline-flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-gray-900">
          <ArrowLeft size={16} /> Back to Jobs
        </Link>

        {/* Header card */}
        <div className="bg-white rounded-2xl border border-gray-100 p-6">
          <div className="flex items-start justify-between gap-6">
            <div className="flex items-center gap-5">
              <div className="w-14 h-14 rounded-xl bg-[#12b388]/10 flex items-center justify-center shrink-0 overflow-hidden">
                {company.company_logo_url && !logoError ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={`${api.defaults.baseURL}${company.company_logo_url}`}
                    alt={`${company.company_name || 'Company'} logo`}
                    className="w-full h-full object-cover"
                    onError={() => setLogoError(true)}
                  />
                ) : (
                  <Building2 size={28} className="text-[#12b388]" />
                )}
              </div>
              <div>
                <h2 className="text-2xl font-bold text-gray-900">{job.jd_name}</h2>
                <p className="text-gray-500 mt-1">{company.company_name || 'Unknown Company'}</p>
                <div className="flex items-center gap-3 mt-2 text-xs text-gray-500 flex-wrap">
                  {(job.location || company.location) && (
                    <span className="inline-flex items-center gap-1"><MapPin size={12} />{job.location || company.location}</span>
                  )}
                  {job.job_type && (
                    <span className="inline-flex items-center gap-1"><Briefcase size={12} />{job.job_type.name}</span>
                  )}
                  {job.job_function && (
                    <span className="px-2.5 py-0.5 bg-gray-100 rounded-full font-medium">{job.job_function.name}</span>
                  )}
                </div>
              </div>
            </div>
            <button
              onClick={handleApply}
              disabled={applying || applied}
              className="px-6 py-2.5 bg-[#12b388] text-white text-sm font-bold rounded-full hover:bg-[#10a078] transition-colors disabled:opacity-50 shrink-0"
            >
              {applied ? 'Applied ✓' : applying ? 'Applying...' : 'Easy Apply'}
            </button>
          </div>

          {/* Company details */}
          {(company.description || company.website || company.industry) && (
            <div className="mt-6 pt-6 border-t border-gray-100">
              <h3 className="text-sm font-bold text-gray-900 uppercase tracking-wider mb-3">About the Company</h3>
              {company.description && <p className="text-sm text-gray-600 whitespace-pre-line">{company.description}</p>}
              <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
                {company.industry && <span className="px-2.5 py-0.5 bg-gray-100 rounded-full font-medium">{company.industry}</span>}
                {company.website && (
                  <a href={company.website} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-[#12b388] font-medium hover:underline">
                    <Globe size={12} />{company.website}
                  </a>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Requirements */}
        <div className="bg-white rounded-2xl border border-gray-100 p-6 space-y-6">
          <div>
            <h3 className="text-lg font-bold text-gray-900 border-b border-gray-100 pb-4">Required Experience</h3>
            <p className="text-sm text-gray-600 mt-4">{job.required_experience ? `${job.required_experience} years` : 'Not specified'}</p>
          </div>
          {(hasStructuredSkills || descFallback.essentialText) && (
            <div>
              <h3 className="text-lg font-bold text-gray-900 border-b border-gray-100 pb-4">Required Skills</h3>
              {hasOverlap && (
                <p className="text-xs text-gray-500 mt-3">
                  <span className="font-bold text-[#12b388]">✓ Green = in your CV</span>
                  <span className="mx-2">•</span>
                  <span className="font-bold text-red-500">Red = missing from your CV</span>
                </p>
              )}
              {essentialSkills.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Essential</p>
                  <div className="flex flex-wrap gap-2">
                    {essentialSkills.map((s: string) => (
                      <span key={`ess-${s}`} className={`px-3 py-1 text-xs font-medium rounded-full ${skillChip(s, 'ess')}`}>
                        {matchedEss.includes(s) ? '✓ ' : missingEss.includes(s) || (hasOverlap && !matchedEss.includes(s)) ? '✗ ' : ''}{s}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {electiveSkills.length > 0 && (
                <div className="mt-4">
                  <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Nice to have</p>
                  <div className="flex flex-wrap gap-2">
                    {electiveSkills.map((s: string) => (
                      <span key={`ele-${s}`} className={`px-3 py-1 text-xs font-medium rounded-full ${skillChip(s, 'ele')}`}>{matchedEle.includes(s) ? '✓ ' : ''}{s}</span>
                    ))}
                  </div>
                </div>
              )}
              {!hasStructuredSkills && descFallback.essentialText && (
                <>
                  <p className="text-xs text-gray-400 mt-3">Structured skills unavailable — divided from description text.</p>
                  <div className="mt-4">
                    <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Essential</p>
                    <p className="text-sm text-gray-600 whitespace-pre-line">{descFallback.essentialText}</p>
                  </div>
                  {descFallback.electiveText && (
                    <div className="mt-4">
                      <p className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-2">Nice to have</p>
                      <p className="text-sm text-gray-600 whitespace-pre-line">{descFallback.electiveText}</p>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
          {job.job_description && (
            <div>
              <h3 className="text-lg font-bold text-gray-900 border-b border-gray-100 pb-4">Full Description</h3>
              <p className="text-sm text-gray-600 mt-4 whitespace-pre-line">{job.job_description}</p>
            </div>
          )}
        </div>

        <ApplyAdviceCard jd_id={jd_id} />
      </div>
    </DashboardLayout>
  );
}
