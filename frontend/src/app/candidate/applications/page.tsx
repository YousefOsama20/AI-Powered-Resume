'use client';

import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import api from '@/lib/axios';

export default function CandidateApplications() {
  const [apps, setApps] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/ats/customer/applications')
      .then(res => {
        setApps(res.data.applications);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  return (
    <DashboardLayout role="CANDIDATE">
      <div className="mb-8">
        <h2 className="text-3xl font-bold text-gray-900">Your Applications</h2>
        <p className="text-gray-500 mt-2">Track the status of jobs you have applied to.</p>
      </div>

      <div className="bg-white border border-gray-200 rounded-2xl overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-gray-50 border-b border-gray-200 text-sm font-bold text-gray-600 uppercase">
            <tr>
              <th className="p-4">Job Title</th>
              <th className="p-4">Company</th>
              <th className="p-4">Status</th>
              <th className="p-4">Applied Date</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={4} className="p-8 text-center text-gray-500">Loading...</td></tr>
            ) : apps.length === 0 ? (
              <tr><td colSpan={4} className="p-8 text-center text-gray-500">You haven't applied to any jobs yet.</td></tr>
            ) : (
              apps.map(app => (
                <tr key={app.application_id} className="border-b border-gray-100 last:border-0 hover:bg-gray-50">
                  <td className="p-4 font-bold text-gray-900">{app.jd_name}</td>
                  <td className="p-4 font-medium text-gray-700">{app.company_name || 'Unknown Company'}</td>
                  <td className="p-4">
                    <span className="px-3 py-1 rounded-full text-xs font-bold bg-[#12b388]/10 text-[#12b388]">
                      {(app.stage || 'APPLIED').replace('_', ' ')}
                    </span>
                  </td>
                  <td className="p-4 text-gray-500 text-sm">{new Date(app.created_at).toLocaleDateString()}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </DashboardLayout>
  );
}
