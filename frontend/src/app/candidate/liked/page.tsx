'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import DashboardLayout from '@/components/DashboardLayout';
import JobTypeFilter, { buildJobTypeQuery, filterJobsByType } from '@/components/JobTypeFilter';
import LikeButton from '@/components/LikeButton';
import api from '@/lib/axios';
import { Briefcase, MapPin, Building2 } from 'lucide-react';

type LikedJob = {
  jd_id: string;
  jd_name: string;
  company_name: string;
  location?: string | null;
  job_type?: { id: string; name: string } | null;
  job_function?: { id: string; name: string } | null;
  created_at?: string | null;
  liked_at?: string | null;
};

export default function LikedJobs() {
  const [jobs, setJobs] = useState<LikedJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [applyingId, setApplyingId] = useState<string | null>(null);

  const fetchJobs = useCallback(async (typeIds: string[]) => {
    setLoading(true);
    try {
      const qs = buildJobTypeQuery(typeIds);
      const res = await api.get(`/ats/customer/likes${qs}`);
      let list: LikedJob[] = res.data.likes || [];
      if (typeIds.length && list.length > 0 && (list[0] as any)?.job_type !== undefined) {
        list = filterJobsByType(list, typeIds);
      }
      setJobs(list);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs(selectedTypes);
  }, [fetchJobs, selectedTypes]);

  const handleApply = async (jd_id: string) => {
    setApplyingId(jd_id);
    try {
      await api.post(`/ats/jobs/${jd_id}/apply`);
      alert('Successfully applied to job!');
    } catch (err: any) {
      alert(err?.response?.data?.message || 'Failed to apply or already applied.');
    } finally {
      setApplyingId(null);
    }
  };

  const isFiltered = selectedTypes.length > 0;

  return (
    <DashboardLayout role="CANDIDATE">
      <div className="flex items-center gap-6 mb-8 border-b border-gray-200 pb-4">
        <h2 className="text-xl font-bold text-gray-900 mr-4">JOBS</h2>
        <div className="flex gap-4 text-sm font-medium">
          <Link href="/candidate/dashboard" className="text-gray-400 hover:text-gray-600 cursor-pointer">Recommended</Link>
          <Link href="/candidate/jobs" className="text-gray-400 hover:text-gray-600 cursor-pointer">Browse All</Link>
          <span className="text-black border-b-2 border-black pb-4 -mb-4 cursor-pointer">Liked</span>
          <Link href="/candidate/applications" className="text-gray-400 hover:text-gray-600 cursor-pointer">Applied</Link>
        </div>
      </div>

      <JobTypeFilter selected={selectedTypes} onChange={setSelectedTypes} />

      <div className="max-w-4xl space-y-4">
        {loading ? (
          <div className="animate-pulse space-y-4">
            {[1, 2, 3].map((i) => (
              <div key={i} className="bg-white rounded-2xl h-32 border border-gray-100" />
            ))}
          </div>
        ) : jobs.length === 0 ? (
          <div className="bg-white rounded-2xl p-12 text-center border border-gray-100">
            {isFiltered ? (
              <>
                <h3 className="text-xl font-bold text-gray-900 mb-2">No liked jobs match this filter</h3>
                <p className="text-gray-500 mb-6">Try selecting more job types, or clear the filter to see everything you liked.</p>
                <button
                  onClick={() => setSelectedTypes([])}
                  className="px-6 py-2.5 bg-gray-900 text-white text-sm font-bold rounded-full hover:bg-gray-700 transition-colors"
                >
                  Show All Liked
                </button>
              </>
            ) : (
              <>
                <h3 className="text-xl font-bold text-gray-900 mb-2">You haven&apos;t liked any jobs yet</h3>
                <p className="text-gray-500 mb-6">Tap the heart on any job to save it here for later.</p>
                <Link
                  href="/candidate/jobs"
                  className="px-6 py-2.5 bg-gray-900 text-white text-sm font-bold rounded-full hover:bg-gray-700 transition-colors inline-block"
                >
                  Browse All Jobs
                </Link>
              </>
            )}
          </div>
        ) : (
          jobs.map((job) => (
            <div
              key={job.jd_id}
              className="bg-white rounded-2xl border border-gray-100 p-5 flex items-center gap-5 hover:shadow-md transition-shadow"
            >
              <div className="w-12 h-12 rounded-xl bg-[#12b388]/10 flex items-center justify-center shrink-0">
                <Building2 size={22} className="text-[#12b388]" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-base font-bold text-gray-900 truncate">
                  <Link href={`/candidate/jobs/${job.jd_id}`} className="hover:text-[#12b388] transition-colors">
                    {job.jd_name}
                  </Link>
                </h3>
                <p className="text-sm text-gray-500 mt-0.5">{job.company_name}</p>
                <div className="flex items-center gap-2 mt-2 text-xs text-gray-500 flex-wrap">
                  {job.location && (
                    <span className="inline-flex items-center gap-1"><MapPin size={12} />{job.location}</span>
                  )}
                  {job.job_type && (
                    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 bg-gray-100 rounded-full font-medium">
                      <Briefcase size={12} />{job.job_type.name}
                    </span>
                  )}
                  {job.job_function && (
                    <span className="px-2.5 py-0.5 bg-[#12b388]/10 text-[#12b388] rounded-full font-medium">
                      {job.job_function.name}
                    </span>
                  )}
                </div>
              </div>
              <div className="flex flex-col items-end gap-2 shrink-0">
                {job.created_at && (
                  <span className="text-xs text-gray-400">{new Date(job.created_at).toLocaleDateString()}</span>
                )}
                <div className="flex gap-2 items-center">
                  <LikeButton
                    jd_id={job.jd_id}
                    initialLiked
                    onToggle={(liked) => {
                      if (!liked) setJobs((prev) => prev.filter((j) => j.jd_id !== job.jd_id));
                    }}
                  />
                  <Link
                    href={`/candidate/jobs/${job.jd_id}`}
                    className="px-4 py-2 bg-white border border-gray-200 text-gray-700 text-xs font-bold rounded-full hover:bg-gray-50 transition-colors"
                  >
                    View
                  </Link>
                  <button
                    onClick={() => handleApply(job.jd_id)}
                    disabled={applyingId === job.jd_id}
                    className="px-4 py-2 bg-[#12b388] text-white text-xs font-bold rounded-full hover:bg-[#10a078] transition-colors disabled:opacity-50"
                  >
                    {applyingId === job.jd_id ? 'Applying…' : 'Easy Apply'}
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </DashboardLayout>
  );
}
