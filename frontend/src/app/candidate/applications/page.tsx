'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import DashboardLayout from '@/components/DashboardLayout';
import api from '@/lib/axios';

type Application = {
  application_id: string;
  company_name: string | null;
  jd_id: string | null;
  jd_name: string | null;
  stage: string;
  created_at: string;
};

const stagePill = (stage: string) => {
  const s = (stage || 'APPLIED').toUpperCase();
  if (s === 'CONTACTED') return 'bg-amber-100 text-amber-700 animate-pulse';
  if (s === 'APPLIED') return 'bg-blue-50 text-blue-600';
  if (s === 'CONSIDERED' || s === 'INTERVIEWING') return 'bg-violet-100 text-violet-700';
  if (s === 'OFFER_SENT' || s === 'HIRED') return 'bg-[#12b388]/10 text-[#12b388]';
  if (s === 'REJECTED' || s === 'CANCELLED') return 'bg-gray-100 text-gray-500';
  return 'bg-[#12b388]/10 text-[#12b388]';
};

export default function CandidateApplications() {
  const [apps, setApps] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [actingId, setActingId] = useState<string | null>(null);

  useEffect(() => {
    api.get('/ats/customer/applications')
      .then(res => {
        setApps(res.data.applications || []);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const handleAccept = async (application_id: string) => {
    setActingId(application_id);
    try {
      await api.put(`/ats/customer/applications/${application_id}/accept`);
      setApps(prev => prev.map(a => a.application_id === application_id ? { ...a, stage: 'CONSIDERED' } : a));
    } catch (err: any) {
      alert(err.response?.data?.message || 'Failed to accept request');
    } finally {
      setActingId(null);
    }
  };

  const handleDecline = async (application_id: string) => {
    if (!confirm('Decline this company request?')) return;
    setActingId(application_id);
    try {
      await api.put(`/ats/customer/applications/${application_id}/decline`);
      setApps(prev => prev.map(a => a.application_id === application_id ? { ...a, stage: 'CANCELLED' } : a));
    } catch (err: any) {
      alert(err.response?.data?.message || 'Failed to decline request');
    } finally {
      setActingId(null);
    }
  };

  const requests = apps.filter(a => (a.stage || '').toUpperCase() === 'CONTACTED');
  const history = apps.filter(a => (a.stage || '').toUpperCase() !== 'CONTACTED');

  return (
    <DashboardLayout role="CANDIDATE">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-gray-900">Your Applications</h2>
        <p className="text-gray-500 mt-2">Company requests and jobs you have applied to.</p>
      </div>

      {/* Incoming company requests */}
      <div className="mb-8">
        <h3 className="text-lg font-bold text-gray-900 mb-4">
          Company Requests {requests.length > 0 && (
            <span className="ml-2 px-2.5 py-0.5 bg-amber-100 text-amber-700 rounded-full text-xs font-bold">{requests.length} new</span>
          )}
        </h3>
        {loading ? (
          <div className="bg-white border border-gray-200 rounded-2xl p-8 text-center text-gray-500">Loading...</div>
        ) : requests.length === 0 ? (
          <div className="bg-white border border-gray-200 rounded-2xl p-8 text-center text-gray-500">
            No company requests right now. When a company contacts you, it will appear here.
          </div>
        ) : (
          <div className="space-y-4">
            {requests.map(req => (
              <div key={req.application_id} className="bg-white border-2 border-amber-200 rounded-2xl p-5 flex flex-col md:flex-row md:items-center gap-4">
                <div className="flex-1">
                  <p className="text-xs font-bold text-amber-600 uppercase tracking-wider mb-1">📩 Company contacted you</p>
                  <p className="text-lg font-bold text-gray-900">{req.jd_name || 'Job opportunity'}</p>
                  <p className="text-sm text-gray-500 mt-1">
                    {req.company_name || 'Unknown Company'} • {req.created_at ? new Date(req.created_at).toLocaleDateString() : ''}
                  </p>
                  {req.jd_id && (
                    <Link href={`/candidate/jobs/${req.jd_id}`} className="text-sm font-bold text-[#12b388] hover:underline mt-2 inline-block">
                      View job details →
                    </Link>
                  )}
                </div>
                <div className="flex gap-3 shrink-0">
                  <button
                    onClick={() => handleAccept(req.application_id)}
                    disabled={actingId === req.application_id}
                    className="px-6 py-2.5 bg-[#12b388] text-white text-sm font-bold rounded-full hover:bg-[#10a078] transition-colors disabled:opacity-50"
                  >
                    {actingId === req.application_id ? 'Working...' : 'Accept ✓'}
                  </button>
                  <button
                    onClick={() => handleDecline(req.application_id)}
                    disabled={actingId === req.application_id}
                    className="px-6 py-2.5 bg-white border border-gray-200 text-gray-700 text-sm font-bold rounded-full hover:bg-gray-50 transition-colors disabled:opacity-50"
                  >
                    Decline
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Full history */}
      <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-gray-50 border-b border-gray-200 text-sm font-bold text-gray-600 uppercase">
            <tr>
              <th className="p-4">Job Title</th>
              <th className="p-4">Company</th>
              <th className="p-4">Status</th>
              <th className="p-4">Date</th>
              <th className="p-4">Action</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="p-8 text-center text-gray-500">Loading...</td></tr>
            ) : apps.length === 0 ? (
              <tr><td colSpan={5} className="p-8 text-center text-gray-500">You haven&apos;t applied to any jobs yet, and no company has contacted you.</td></tr>
            ) : (
              [...requests, ...history].map(app => {
                const isRequest = (app.stage || '').toUpperCase() === 'CONTACTED';
                return (
                  <tr key={app.application_id} className={`border-b border-gray-100 last:border-0 hover:bg-gray-50 ${isRequest ? 'bg-amber-50/50' : ''}`}>
                    <td className="p-4 font-bold text-gray-900">
                      {app.jd_id ? (
                        <Link href={`/candidate/jobs/${app.jd_id}`} className="hover:text-[#12b388] transition-colors">
                          {app.jd_name}
                        </Link>
                      ) : (app.jd_name)}
                    </td>
                    <td className="p-4 font-medium text-gray-700">{app.company_name || 'Unknown Company'}</td>
                    <td className="p-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-bold ${stagePill(app.stage)}`}>
                        {(app.stage || 'APPLIED').replace('_', ' ')}
                      </span>
                    </td>
                    <td className="p-4 text-gray-500 text-sm">{app.created_at ? new Date(app.created_at).toLocaleDateString() : ''}</td>
                    <td className="p-4">
                      {isRequest ? (
                        <div className="flex gap-2">
                          <button
                            onClick={() => handleAccept(app.application_id)}
                            disabled={actingId === app.application_id}
                            className="px-4 py-1.5 bg-[#12b388] text-white text-xs font-bold rounded-full hover:bg-[#10a078] disabled:opacity-50"
                          >
                            Accept
                          </button>
                          <button
                            onClick={() => handleDecline(app.application_id)}
                            disabled={actingId === app.application_id}
                            className="px-4 py-1.5 bg-white border border-gray-200 text-gray-600 text-xs font-bold rounded-full hover:bg-gray-50 disabled:opacity-50"
                          >
                            Decline
                          </button>
                        </div>
                      ) : (
                        <span className="text-xs text-gray-400">—</span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </DashboardLayout>
  );
}
