'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import DashboardLayout from '@/components/DashboardLayout';
import api from '@/lib/axios';
import { Plus, Users, ChevronRight, Pencil, Trash2 } from 'lucide-react';

export default function CompanyJobs() {
  const [jds, setJds] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchJds = () => {
    api.get('/nlp/jd')
      .then(res => {
        setJds(res.data.jds || []);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchJds();
  }, []);

  const handleDelete = async (jd_id: string, jd_name: string) => {
    if (!confirm(`Delete "${jd_name}"? This will remove it from the vector store and delete all its applications.`)) return;
    setDeletingId(jd_id);
    try {
      await api.delete(`/nlp/jd/${jd_id}`);
      setJds(prev => prev.filter(jd => jd.jd_id !== jd_id));
    } catch (err) {
      console.error(err);
      alert('Failed to delete job posting');
    }
    setDeletingId(null);
  };

  return (
    <DashboardLayout role="COMPANY">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h2 className="text-3xl font-bold text-gray-900">Job Descriptions</h2>
          <p className="text-gray-500 mt-2">Manage your active job postings and create new ones.</p>
        </div>
        <Link
          href="/company/jobs/new"
          className="flex items-center gap-2 px-6 py-2.5 bg-black text-white font-medium rounded-full hover:bg-gray-800 transition-colors"
        >
          <Plus size={16} />
          Create New JD
        </Link>
      </div>

      <div className="space-y-4">
        {loading ? (
          [1, 2, 3].map(i => <div key={i} className="bg-white h-28 rounded-2xl border border-gray-100 animate-pulse" />)
        ) : jds.length === 0 ? (
          <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center">
            <h3 className="text-xl font-bold text-gray-900 mb-2">No job postings yet</h3>
            <p className="text-gray-500 mb-6">Create your first Job Description to start receiving AI-matched candidates.</p>
            <Link
              href="/company/jobs/new"
              className="inline-flex items-center gap-2 px-6 py-2.5 bg-[#12b388] text-white font-bold rounded-full hover:bg-[#10a078] transition-colors"
            >
              <Plus size={16} />
              Create First JD
            </Link>
          </div>
        ) : (
          jds.map(jd => (
            <div key={jd.jd_id} className="bg-white rounded-2xl border border-gray-100 p-6 flex items-center justify-between hover:shadow-md transition-shadow">
              <div className="flex items-center gap-5">
                <div className="w-12 h-12 rounded-xl bg-[#12b388]/10 flex items-center justify-center">
                  <Users size={24} className="text-[#12b388]" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-gray-900">{jd.jd_name}</h3>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs font-bold px-2.5 py-0.5 bg-green-50 text-green-600 rounded-full">ACTIVE</span>
                    <span className="text-xs text-gray-500">{jd.location || 'Remote'}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <Link
                  href={`/company/jobs/${jd.jd_id}/matches`}
                  className="flex items-center gap-2 px-5 py-2.5 bg-black text-white font-bold rounded-xl hover:bg-gray-800 transition-colors"
                >
                  AI Match
                </Link>
                <Link
                  href={`/company/ats/${jd.jd_id}`}
                  className="flex items-center gap-2 px-5 py-2.5 bg-[#12b388]/10 text-[#12b388] font-bold rounded-xl hover:bg-[#12b388]/20 transition-colors"
                >
                  ATS
                  <ChevronRight size={16} />
                </Link>
                <Link
                  href={`/company/jobs/${jd.jd_id}/edit`}
                  title="Edit job posting"
                  className="p-2.5 border border-gray-200 text-gray-500 rounded-xl hover:bg-gray-50 hover:text-gray-900 transition-colors"
                >
                  <Pencil size={16} />
                </Link>
                <button
                  onClick={() => handleDelete(jd.jd_id, jd.jd_name)}
                  disabled={deletingId === jd.jd_id}
                  title="Delete job posting"
                  className="p-2.5 border border-gray-200 text-gray-500 rounded-xl hover:bg-red-50 hover:text-red-600 hover:border-red-200 transition-colors disabled:opacity-50"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </DashboardLayout>
  );
}
