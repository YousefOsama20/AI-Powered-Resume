'use client';

import { useEffect } from 'react';
import MatchRing from '@/components/MatchRing';
import CandidateAvatar from '@/components/CandidateAvatar';
import { UserPlus, X } from 'lucide-react';

interface CandidatePreviewModalProps {
  match: any;
  onClose: () => void;
  onContact: (customerId: string) => void;
}

export default function CandidatePreviewModal({ match, onClose, onContact }: CandidatePreviewModalProps) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handler);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handler);
      document.body.style.overflow = '';
    };
  }, [onClose]);

  const overall = Math.round(match.match_score || 0);
  const skill = Math.round(match.keyword_score ?? 0);
  const ess = Math.round(match.essential_score ?? 0);
  const ele = Math.round(match.elective_score ?? 0);
  const sem = Math.round(match.semantic_score ?? 0);
  const exp = Math.round(match.experience_score ?? 0);
  const typeScore = Math.round(match.job_type_score ?? 0);
  const funcScore = Math.round(match.job_function_score ?? 0);
  const matchedEss: string[] = match.matched_essential_skills || [];
  const missingEss: string[] = match.missing_essential_skills || [];
  const matchedEle: string[] = match.matched_elective_skills || [];
  const missingEle: string[] = match.missing_elective_skills || [];
  const contacted = !!match.has_accepted_request;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between p-6 border-b border-gray-100">
          <div className="flex items-center gap-4">
            <CandidateAvatar photoUrl={match.candidate_photo_url} name={match.candidate_name} size={56} />
            <div>
            <h3 className="text-2xl font-bold text-gray-900">{match.candidate_name || 'Anonymous Candidate'}</h3>
            <div className="flex items-center gap-3 mt-2 text-sm text-gray-500 flex-wrap">
              <span>📍 {match.candidate_location || 'Remote'}</span>
              {(match.file_name || match.file_id) && (
                <span className="text-xs bg-gray-100 px-2 py-1 rounded-full">📄 {match.file_name || match.file_id}</span>
              )}
              {typeof match.candidate_experience === 'number' && (
                <span className="text-xs bg-gray-100 px-2 py-1 rounded-full">{match.candidate_experience} yrs exp</span>
              )}
            </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-full hover:bg-gray-100 text-gray-400 hover:text-gray-900 transition-colors"
            aria-label="Close preview"
          >
            <X size={20} />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Score rings */}
          <div className="flex items-center gap-6 flex-wrap">
            <MatchRing percentage={overall} label="Overall" size={72} />
            <div title={`Essential ${ess}% • Elective ${ele}% • Semantic ${sem}%`}>
              <MatchRing percentage={skill} label="Skills" size={72} />
            </div>
            <MatchRing percentage={exp} label="Experience" size={72} />
            <MatchRing percentage={typeScore} label="Job Type" size={72} />
            <MatchRing percentage={funcScore} label="Function" size={72} />
          </div>

          {/* Skills breakdown */}
          <div>
            <h4 className="text-sm font-bold text-gray-900 uppercase tracking-wider mb-3">Skill Breakdown</h4>
            {matchedEss.length > 0 && (
              <div className="mb-3">
                <p className="text-xs font-bold text-[#12b388] mb-2">✓ Matched essential ({matchedEss.length})</p>
                <div className="flex flex-wrap gap-1.5">
                  {matchedEss.map((s: string) => (
                    <span key={`m-${s}`} className="px-2.5 py-0.5 text-xs font-medium bg-[#12b388]/10 text-[#12b388] rounded-full">{s}</span>
                  ))}
                </div>
              </div>
            )}
            {missingEss.length > 0 && (
              <div className="mb-3">
                <p className="text-xs font-bold text-red-500 mb-2">✗ Missing essential ({missingEss.length})</p>
                <div className="flex flex-wrap gap-1.5">
                  {missingEss.map((s: string) => (
                    <span key={`x-${s}`} className="px-2.5 py-0.5 text-xs font-medium bg-red-50 text-red-500 rounded-full">{s}</span>
                  ))}
                </div>
              </div>
            )}
            {(matchedEle.length > 0 || missingEle.length > 0) && (
              <div>
                <p className="text-xs font-bold text-gray-500 mb-2">Nice to have</p>
                <div className="flex flex-wrap gap-1.5">
                  {matchedEle.map((s: string) => (
                    <span key={`me-${s}`} className="px-2.5 py-0.5 text-xs font-medium bg-[#12b388]/10 text-[#12b388] rounded-full">✓ {s}</span>
                  ))}
                  {missingEle.map((s: string) => (
                    <span key={`xe-${s}`} className="px-2.5 py-0.5 text-xs font-medium bg-gray-100 text-gray-500 rounded-full">{s}</span>
                  ))}
                </div>
              </div>
            )}
            {matchedEss.length === 0 && missingEss.length === 0 && matchedEle.length === 0 && (
              <p className="text-sm text-gray-400">No structured skill overlap for this candidate.</p>
            )}
          </div>

          {/* Experience */}
          <div>
            <h4 className="text-sm font-bold text-gray-900 uppercase tracking-wider mb-2">Experience</h4>
            <p className="text-sm text-gray-600">
              Required: <span className="font-bold text-gray-900">{match.required_experience ?? '—'} yrs</span>
              <span className="mx-2">•</span>
              Candidate: <span className="font-bold text-gray-900">{match.candidate_experience ?? '—'} yrs</span>
              {typeof match.experience_gap === 'number' && match.experience_gap > 0 && (
                <span className="ml-2 text-xs font-bold text-amber-600 bg-amber-100 px-2 py-0.5 rounded-full">Gap: {match.experience_gap} yrs</span>
              )}
            </p>
          </div>

          <p className="text-xs text-gray-400">
            Contact details and full CV unlock after the candidate accepts your contact (CONSIDERED stage).
          </p>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-100">
          <button
            onClick={onClose}
            className="px-6 py-2.5 rounded-full border border-gray-200 text-sm font-bold text-gray-600 hover:bg-gray-50 transition-colors"
          >
            Close
          </button>
          <button
            onClick={() => onContact(match.customer_id)}
            disabled={contacted}
            className={`px-6 py-2.5 rounded-full text-sm font-bold flex items-center gap-2 transition-colors ${contacted ? 'bg-gray-100 text-gray-400 cursor-not-allowed' : 'bg-[#12b388] text-white hover:bg-[#10a078]'}`}
          >
            <UserPlus size={16} />
            {contacted ? 'Contacted' : 'Contact Candidate'}
          </button>
        </div>
      </div>
    </div>
  );
}
