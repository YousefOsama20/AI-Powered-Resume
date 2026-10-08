'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import DashboardLayout from '@/components/DashboardLayout';
import MatchRing from '@/components/MatchRing';
import CandidatePreviewModal from '@/components/CandidatePreviewModal';
import CandidateAvatar from '@/components/CandidateAvatar';
import api from '@/lib/axios';
import { UserPlus, ArrowLeft } from 'lucide-react';

export default function MatchesClient({ jd_id }: { jd_id: string }) {
  const [matches, setMatches] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<any | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    api.post('/nlp/match', { jd_id, top_k: 10 })
      .then(res => {
        if (res.data?.signal === 'match_failed') {
          setError('The AI matching service failed. Please try again later.');
        } else {
          setMatches(res.data.results || []);
        }
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        const status = err?.response?.status;
        const message = err?.response?.data?.message;
        if (status === 404) {
          setError(message || 'Job description not found or you do not have permission to view it.');
        } else {
          setError(message || 'Failed to load matches. Please try again.');
        }
        setLoading(false);
      });
  }, [jd_id]);

  const handleContact = async (candidateId: string) => {
    try {
      await api.post('/ats/company/contact', { jd_id, customer_id: candidateId });
      alert('Candidate added to ATS Pipeline in CONTACTED stage!');
      // Update UI (list + open modal, if any)
      setMatches(prev => prev.map(m => m.customer_id === candidateId ? { ...m, has_accepted_request: true } : m));
      setSelected((prev: any) => prev && prev.customer_id === candidateId ? { ...prev, has_accepted_request: true } : prev);
    } catch (err: any) {
      alert(err.response?.data?.message || 'Failed to contact candidate');
    }
  };

  return (
    <DashboardLayout role="COMPANY">
      <div className="mb-8">
        <Link href="/company/jobs" className="inline-flex items-center text-sm text-gray-500 hover:text-gray-900 mb-4">
          <ArrowLeft size={16} className="mr-1" /> Back to Jobs
        </Link>
        <h2 className="text-3xl font-bold text-gray-900">Top AI Matches</h2>
        <p className="text-gray-500 mt-2">
          {matches.length > 0
            ? `Top ${matches.length} candidate${matches.length === 1 ? '' : 's'} matched globally across all CVs, ranked by AI score.`
            : 'Candidates matched globally across the platform based on AI analysis.'}
        </p>
      </div>

      <div className="space-y-6">
        {loading ? (
          [1, 2, 3].map(i => <div key={i} className="bg-white h-48 rounded-2xl border border-gray-100 animate-pulse" />)
        ) : error ? (
          <div className="bg-white rounded-2xl border border-red-100 p-12 text-center">
            <h3 className="text-xl font-bold text-gray-900 mb-2">Couldn&apos;t load matches</h3>
            <p className="text-gray-500">{error}</p>
          </div>
        ) : matches.length === 0 ? (
          <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center">
            <h3 className="text-xl font-bold text-gray-900 mb-2">No matches found</h3>
            <p className="text-gray-500">We couldn&apos;t find any candidates matching this job description. Make sure candidates have uploaded and indexed their CVs.</p>
          </div>
        ) : (
          matches.map((match) => {
            const overallMatch = Math.round(match.match_score || 0);
            const expMatch = Math.round(match.experience_score || 0);
            const skillMatch = Math.round(((match.keyword_score || 0) + (match.semantic_score || 0)) / 2);
            const rowKey = match.candidate_id || match.file_id || match.customer_id;

            return (
              <div key={rowKey} className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden flex flex-col hover:shadow-md transition-shadow">
                <div className="flex flex-col lg:flex-row">
                  <div className="lg:w-64 bg-gray-900 text-white p-6 flex flex-col items-center justify-center text-center relative overflow-hidden">
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
                      MATCH SCORE
                    </span>
                    <button 
                      onClick={() => handleContact(match.customer_id)}
                      disabled={match.has_accepted_request}
                      className={`w-full py-3 px-4 font-bold rounded-xl flex items-center justify-center gap-2 transition-colors ${match.has_accepted_request ? 'bg-gray-800 text-gray-500 cursor-not-allowed' : 'bg-[#12b388] text-white hover:bg-[#10a078]'}`}
                    >
                      <UserPlus size={18} />
                      {match.has_accepted_request ? 'Contacted' : 'Contact Candidate'}
                    </button>
                  </div>

                  <div className="flex-1 p-6 lg:p-8">
                    <div className="flex justify-between items-start mb-6">
                      <div className="flex items-center gap-4">
                        <CandidateAvatar photoUrl={match.candidate_photo_url} name={match.candidate_name} size={56} />
                        <div>
                        <h3
                          className="text-2xl font-bold text-gray-900 mb-2 hover:text-[#12b388] cursor-pointer transition-colors"
                          onClick={() => setSelected(match)}
                          title="View full candidate breakdown"
                        >
                          {match.candidate_name || 'Anonymous Candidate'}
                        </h3>
                        <div className="flex items-center gap-4 text-sm text-gray-500 flex-wrap">
                          <span className="flex items-center gap-1">📍 {match.candidate_location || 'Remote'}</span>
                          {(match.file_name || match.file_id) && (
                            <span className="text-xs bg-gray-100 px-2 py-1 rounded-full">📄 {match.file_name || match.file_id}</span>
                          )}
                          {typeof match.candidate_experience === 'number' && (
                            <span className="text-xs bg-gray-100 px-2 py-1 rounded-full">{match.candidate_experience} yrs exp</span>
                          )}
                        </div>
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-3 gap-6">
                      <MatchRing percentage={skillMatch} label="Skills" size={64} />
                      <MatchRing percentage={expMatch} label="Experience" size={64} />
                      <MatchRing percentage={Math.round(match.job_type_score || 0)} label="Job Type" size={64} />
                    </div>
                    <button
                      onClick={() => setSelected(match)}
                      className="mt-4 text-sm font-bold text-[#12b388] hover:underline"
                    >
                      View full breakdown →
                    </button>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
      {selected && (
        <CandidatePreviewModal
          match={selected}
          onClose={() => setSelected(null)}
          onContact={handleContact}
        />
      )}
    </DashboardLayout>
  );
}
