'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import DashboardLayout from '@/components/DashboardLayout';
import MatchRing from '@/components/MatchRing';
import JobTypeFilter, { buildJobTypeQuery, filterJobsByType } from '@/components/JobTypeFilter';
import LikeButton from '@/components/LikeButton';
import api from '@/lib/axios';
import { Briefcase, MapPin } from 'lucide-react';

export default function CandidateDashboard() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [likedIds, setLikedIds] = useState<string[]>([]);

  const fetchJobs = useCallback(async (typeIds: string[]) => {
    setLoading(true);
    try {
      // Server-side filter: ?top_k=10&job_type_id=A&job_type_id=B (multi-select).
      const qs = buildJobTypeQuery(typeIds, { top_k: 10 });
      const [res, likesRes] = await Promise.all([
        api.get(`/nlp/recommend-jobs${qs}`),
        api.get('/ats/customer/likes/ids').catch(() => ({ data: { jd_ids: [] } })),
      ]);
      setLikedIds(likesRes.data?.jd_ids || []);
      let list: any[] = res.data.recommended_jobs || [];
      // Client-side safety net: instant + guards against stale/unfiltered payloads.
      // Only applies when the payload actually carries job_type (new backend).
      if (typeIds.length && list.length > 0 && list[0]?.job_type !== undefined) {
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
    try {
      await api.post(`/ats/jobs/${jd_id}/apply`);
      alert('Successfully applied to job!');
    } catch (err) {
      alert('Failed to apply or already applied.');
    }
  };

  const isFiltered = selectedTypes.length > 0;

  return (
    <DashboardLayout role="CANDIDATE">
      {/* Top Bar / Filters */}
      <div className="flex items-center gap-6 mb-8 border-b border-gray-200 pb-4">
        <h2 className="text-xl font-bold text-gray-900 mr-4">JOBS</h2>
        <div className="flex gap-4 text-sm font-medium">
          <span className="text-black border-b-2 border-black pb-4 -mb-4 cursor-pointer">Recommended</span>
          <Link href="/candidate/jobs" className="text-gray-400 hover:text-gray-600 cursor-pointer">Browse All</Link>
          <Link href="/candidate/liked" className="text-gray-400 hover:text-gray-600 cursor-pointer">Liked</Link>
          <Link href="/candidate/applications" className="text-gray-400 hover:text-gray-600 cursor-pointer">Applied</Link>
        </div>
      </div>

      <JobTypeFilter selected={selectedTypes} onChange={setSelectedTypes} />

      {/* Main Feed */}
      <div className="max-w-4xl space-y-6">
        {loading ? (
          <div className="animate-pulse space-y-6">
            {[1, 2, 3].map(i => (
              <div key={i} className="bg-white rounded-2xl h-64 border border-gray-100"></div>
            ))}
          </div>
        ) : jobs.length === 0 ? (
          <div className="bg-white rounded-2xl p-12 text-center border border-gray-100">
            {isFiltered ? (
              <>
                <h3 className="text-xl font-bold text-gray-900 mb-2">No jobs match this filter</h3>
                <p className="text-gray-500 mb-6">Try selecting more job types, or clear the filter to see all recommendations.</p>
                <button
                  onClick={() => setSelectedTypes([])}
                  className="px-6 py-2.5 bg-gray-900 text-white text-sm font-bold rounded-full hover:bg-gray-700 transition-colors"
                >
                  Show All Jobs
                </button>
              </>
            ) : (
              <>
                <h3 className="text-xl font-bold text-gray-900 mb-2">No jobs matched yet</h3>
                <p className="text-gray-500">We are still analyzing your profile or there are no JDs in the system.</p>
              </>
            )}
          </div>
        ) : (
          jobs.map((job) => {
            const overallMatch = Math.round(job.match_score || 0);
            const expMatch = Math.round(job.experience_score || 0);
            // Skill Match is the TRUE keyword score (essential/elective overlap).
            // Semantic similarity is shown separately in the tooltip — previously
            // these were averaged, which hid the real skill gap (e.g. 7%).
            const skillMatch = Math.round(job.keyword_score ?? 0);
            const semMatch = Math.round(job.semantic_score ?? 0);
            const lowSkill = skillMatch < 30;
            const matchedEss: string[] = job.matched_essential_skills || [];
            const missingEss: string[] = job.missing_essential_skills || [];
            const matchedEle: string[] = job.matched_elective_skills || [];

            return (
              <div key={job.jd_id} className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden flex flex-col hover:shadow-md transition-shadow">
                <div className="p-6 flex items-start justify-between">
                  {/* Left Content */}
                  <div className="flex-1 pr-8">
                    <div className={`flex items-center gap-2 text-xs font-medium px-3 py-1 rounded-full w-max mb-4 ${lowSkill ? 'text-amber-700 bg-amber-100' : 'text-[#12b388] bg-[#12b388]/10'}`}>
                      {lowSkill ? '⚠️ Low skill overlap — strong on experience' : '✨ Why This Job Is A Match'}
                    </div>
                    <div className="flex items-start gap-2">
                      <h3 className="text-xl font-bold text-gray-900 flex-1">
                        <Link href={`/candidate/jobs/${job.jd_id}`} className="hover:text-[#12b388] transition-colors">
                          {job.jd_name}
                        </Link>
                      </h3>
                      <LikeButton jd_id={job.jd_id} initialLiked={likedIds.includes(job.jd_id)} />
                    </div>
                    <p className="text-sm text-gray-500 mt-1 line-clamp-2">{job.company_name} • Required Exp: {job.required_experience} yrs</p>
                    <div className="flex items-center gap-2 mt-2 text-xs text-gray-500 flex-wrap">
                      {(job.location) && (
                        <span className="inline-flex items-center gap-1"><MapPin size={12} />{job.location}</span>
                      )}
                      {job.job_type && (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 bg-gray-100 rounded-full font-medium">
                          <Briefcase size={12} />{job.job_type.name}
                        </span>
                      )}
                      {job.job_function && (
                        <span className="px-2.5 py-0.5 bg-[#12b388]/10 text-[#12b388] rounded-full font-medium">{job.job_function.name}</span>
                      )}
                    </div>

                    {/* Progress Rings */}
                    <div className="flex items-center gap-8 mt-8">
                      <MatchRing percentage={expMatch} label="Experience Level" />
                      <div title={`Keyword ${skillMatch}% (essential ${Math.round(job.essential_score ?? 0)}%, elective ${Math.round(job.elective_score ?? 0)}%) • Semantic ${semMatch}%`}>
                        <MatchRing percentage={skillMatch} label="Skill Match" />
                      </div>
                    </div>
                    {/* Honest skill breakdown */}
                    {(matchedEss.length > 0 || missingEss.length > 0) && (
                      <div className="mt-4 text-xs">
                        {matchedEss.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 mb-2">
                            <span className="font-bold text-gray-500 uppercase tracking-wider mr-1">You have:</span>
                            {matchedEss.slice(0, 6).map((s: string) => (
                              <span key={`m-${s}`} className="px-2.5 py-0.5 bg-[#12b388]/10 text-[#12b388] rounded-full font-medium">{s}</span>
                            ))}
                            {matchedEle.slice(0, 3).map((s: string) => (
                              <span key={`me-${s}`} className="px-2.5 py-0.5 bg-gray-100 text-gray-600 rounded-full font-medium">{s}</span>
                            ))}
                          </div>
                        )}
                        {missingEss.length > 0 && (
                          <div className="flex flex-wrap gap-1.5">
                            <span className="font-bold text-gray-500 uppercase tracking-wider mr-1">Missing:</span>
                            {missingEss.slice(0, 6).map((s: string) => (
                              <span key={`x-${s}`} className="px-2.5 py-0.5 bg-red-50 text-red-500 rounded-full font-medium">{s}</span>
                            ))}
                            {missingEss.length > 6 && (
                              <span className="text-gray-400">+{missingEss.length - 6} more</span>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  {/* Right Content - The Dark Badge */}
                  <div className="w-56 bg-gray-900 rounded-xl p-6 text-center text-white flex flex-col items-center shrink-0">
                    <div className="relative w-20 h-20 mb-3">
                      <svg className="transform -rotate-90 w-full h-full">
                        <circle cx="40" cy="40" r="36" stroke="rgba(255,255,255,0.2)" strokeWidth="6" fill="transparent" />
                        <circle cx="40" cy="40" r="36" stroke="#12b388" strokeWidth="6" fill="transparent"
                          strokeDasharray={226} strokeDashoffset={226 - ((isNaN(overallMatch) ? 0 : overallMatch) / 100) * 226} strokeLinecap="round" />
                      </svg>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-xl font-bold">{isNaN(overallMatch) ? 0 : overallMatch}%</span>
                      </div>
                    </div>
                    <span className="text-xs font-bold tracking-widest uppercase mb-6 text-[#12b388]">
                      {overallMatch >= 80 ? 'Strong Match' : overallMatch >= 60 ? 'Good Match' : 'Fair Match'}
                    </span>
                    <button
                      onClick={() => handleApply(job.jd_id)}
                      className="w-full py-2.5 rounded-full bg-[#12b388] hover:bg-[#10a078] text-white text-sm font-bold transition-colors"
                    >
                      EASY APPLY
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </DashboardLayout>
  );
}
