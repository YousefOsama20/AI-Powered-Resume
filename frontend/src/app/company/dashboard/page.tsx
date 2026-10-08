'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import DashboardLayout from '@/components/DashboardLayout';
import api from '@/lib/axios';

export default function CompanyDashboard() {
  const [jds, setJds] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/nlp/jd')
      .then(res => {
        setJds(res.data.jds);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  return (
    <DashboardLayout role="COMPANY">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Your Job Postings</h2>
          <p className="text-gray-500 mt-1">Manage your active job descriptions and view applicants.</p>
        </div>
        <Link 
          href="/company/jobs/new"
          className="px-6 py-2.5 bg-black text-white font-medium rounded-full hover:bg-gray-800 transition-colors"
        >
          + Create New JD
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {loading ? (
          [1,2,3].map(i => <div key={i} className="bg-white h-48 rounded-2xl border border-gray-100 animate-pulse"></div>)
        ) : jds.length === 0 ? (
          <div className="col-span-full bg-white rounded-2xl p-12 text-center border border-gray-100">
            <h3 className="text-xl font-bold text-gray-900 mb-2">No active jobs</h3>
            <p className="text-gray-500">Create your first Job Description to start receiving candidates.</p>
          </div>
        ) : (
          jds.map(jd => (
            <div key={jd.jd_id} className="bg-white rounded-2xl border border-gray-100 p-6 flex flex-col justify-between hover:shadow-md transition-shadow">
              <div>
                <h3 className="text-xl font-bold text-gray-900 mb-2">{jd.jd_name}</h3>
                <span className="inline-block px-3 py-1 bg-green-50 text-green-700 text-xs font-bold rounded-full mb-4">ACTIVE</span>
                <p className="text-sm text-gray-500 line-clamp-2">{jd.location ? `Location: ${jd.location}` : 'Anywhere'}</p>
              </div>
              <div className="mt-6 pt-6 border-t border-gray-100 flex gap-3">
                <Link 
                  href={`/company/jobs/${jd.jd_id}/matches`}
                  className="flex-1 text-center py-2 bg-black text-white font-bold rounded-xl hover:bg-gray-800 transition-colors"
                >
                  AI Match
                </Link>
                <Link 
                  href={`/company/ats/${jd.jd_id}`}
                  className="flex-1 text-center py-2 bg-[#12b388]/10 text-[#12b388] font-bold rounded-xl hover:bg-[#12b388]/20 transition-colors"
                >
                  ATS Board
                </Link>
              </div>
            </div>
          ))
        )}
      </div>
    </DashboardLayout>
  );
}
