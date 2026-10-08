'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import DashboardLayout from '@/components/DashboardLayout';
import api from '@/lib/axios';

const STAGES = ['APPLIED', 'CONSIDERED', 'INTERVIEWING', 'OFFER_SENT', 'HIRED', 'REJECTED'];

const STAGE_COLORS: Record<string, string> = {
  'APPLIED': 'bg-blue-50 border-blue-200 text-blue-700',
  'CONSIDERED': 'bg-purple-50 border-purple-200 text-purple-700',
  'INTERVIEWING': 'bg-yellow-50 border-yellow-200 text-yellow-700',
  'OFFER_SENT': 'bg-orange-50 border-orange-200 text-orange-700',
  'HIRED': 'bg-green-50 border-green-200 text-green-700',
  'REJECTED': 'bg-red-50 border-red-200 text-red-700',
};

export default function ATSClient({ jd_id }: { jd_id: string }) {
  const [board, setBoard] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const fetchBoard = async () => {
    try {
      const res = await api.get(`/ats/board/${jd_id}`);
      setBoard(res.data);
      setLoading(false);
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBoard();
  }, [jd_id]);

  const handleDragStart = (e: React.DragEvent, applicationId: string) => {
    e.dataTransfer.setData('applicationId', applicationId);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = async (e: React.DragEvent, targetStage: string) => {
    e.preventDefault();
    const applicationId = e.dataTransfer.getData('applicationId');
    if (!applicationId) return;

    try {
      // Optimistic update
      const newBoard = { ...board };
      let movedApp = null;
      
      // Find and remove from old column
      for (const stage of STAGES) {
        if (newBoard.board[stage]) {
          const idx = newBoard.board[stage].findIndex((a: any) => a.application_id === applicationId);
          if (idx !== -1) {
            movedApp = newBoard.board[stage].splice(idx, 1)[0];
            break;
          }
        }
      }

      if (movedApp) {
        if (!newBoard.board[targetStage]) newBoard.board[targetStage] = [];
        newBoard.board[targetStage].push(movedApp);
        setBoard(newBoard);
      }

      // API Call
      await api.put(`/ats/board/${applicationId}/move`, { stage: targetStage });
    } catch (err) {
      console.error(err);
      alert('Failed to move candidate');
      fetchBoard(); // Revert on failure
    }
  };

  const handleDownloadCV = async (customerId: string) => {
    try {
      const res = await api.get(`/data/download/candidate/${customerId}`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'resume.pdf');
      document.body.appendChild(link);
      link.click();
    } catch (err) {
      alert('Cannot download CV. Candidate must be in CONSIDERED stage or later.');
    }
  };

  if (loading) return <DashboardLayout role="COMPANY"><div className="p-8">Loading Board...</div></DashboardLayout>;
  if (!board) return <DashboardLayout role="COMPANY"><div className="p-8">Failed to load board.</div></DashboardLayout>;

  return (
    <DashboardLayout role="COMPANY">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-gray-900">{board.jd_name}</h2>
        <p className="text-gray-500 mt-2">ATS Pipeline</p>
      </div>

      <div className="flex gap-6 overflow-x-auto pb-8 h-[calc(100vh-200px)]">
        {STAGES.map((stage) => (
          <div 
            key={stage} 
            className={`flex-shrink-0 w-80 rounded-2xl flex flex-col border-2 ${STAGE_COLORS[stage].replace('text-', 'border-').replace('50', '100')} bg-gray-50`}
            onDragOver={handleDragOver}
            onDrop={(e) => handleDrop(e, stage)}
          >
            {/* Column Header */}
            <div className={`p-4 border-b-2 rounded-t-xl font-bold text-sm tracking-widest ${STAGE_COLORS[stage]}`}>
              {stage.replace('_', ' ')}
              <span className="ml-2 px-2 py-0.5 bg-white rounded-full text-xs opacity-80">
                {board.board[stage]?.length || 0}
              </span>
            </div>

            {/* Column Body */}
            <div className="flex-1 p-3 overflow-y-auto space-y-3">
              {(board.board[stage] || []).map((app: any) => (
                <div 
                  key={app.application_id} 
                  draggable
                  onDragStart={(e) => handleDragStart(e, app.application_id)}
                  className="bg-white p-4 rounded-xl border border-gray-200 shadow-sm cursor-grab hover:shadow-md transition-shadow active:cursor-grabbing"
                >
                  <div className="flex justify-between items-start mb-2">
                    <h4 className="font-bold text-gray-900">{app.candidate_name || 'Candidate'}</h4>
                    <span className="text-xs font-bold px-2 py-1 bg-[#12b388]/10 text-[#12b388] rounded-md">
                      {Math.round((app.match_score || 0) * 100)}% Match
                    </span>
                  </div>
                  {(app.candidate_email || app.candidate_phone) && (
                    <div className="text-xs text-gray-600 space-y-0.5 mb-3">
                      {app.candidate_email && (
                        <p className="truncate" title={app.candidate_email}>✉️ {app.candidate_email}</p>
                      )}
                      {app.candidate_phone && (
                        <p>📞 {app.candidate_phone}</p>
                      )}
                    </div>
                  )}
                  <p className="text-xs text-gray-500 mb-4">Applied: {new Date(app.created_at).toLocaleDateString()}</p>
                  
                  {['CONSIDERED', 'INTERVIEWING', 'OFFER_SENT', 'HIRED'].includes(stage) && (
                    <button 
                      onClick={() => handleDownloadCV(app.candidate_id)}
                      className="w-full py-2 text-xs font-bold border border-gray-200 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors"
                    >
                      Download CV
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </DashboardLayout>
  );
}
