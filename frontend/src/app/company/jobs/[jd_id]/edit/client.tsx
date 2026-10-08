'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import DashboardLayout from '@/components/DashboardLayout';
import api from '@/lib/axios';
import { ArrowLeft } from 'lucide-react';

export default function EditJDClient({ jd_id }: { jd_id: string }) {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [taxonomy, setTaxonomy] = useState<{job_types: any[], job_functions: any[]}>({ job_types: [], job_functions: [] });

  const [jdName, setJdName] = useState('');
  const [jobDescription, setJobDescription] = useState('');
  const [location, setLocation] = useState('');
  const [jobTypeId, setJobTypeId] = useState('');
  const [jobFunctionId, setJobFunctionId] = useState('');
  const [isPublic, setIsPublic] = useState(1);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    api.get('/profile/taxonomy').then(res => setTaxonomy(res.data)).catch(console.error);
    // Load SQL metadata (name, location, visibility) from the company JD list
    api.get('/nlp/jd')
      .then(res => {
        const jd = (res.data.jds || []).find((j: any) => j.jd_id === jd_id);
        if (!jd) {
          setNotFound(true);
          setLoading(false);
          return;
        }
        setJdName(jd.jd_name);
        setLocation(jd.location || '');
        setIsPublic(jd.is_public ?? 1);
        // Prefill the raw description text when the JD is public
        api.get(`/ats/jobs/public/${jd_id}`)
          .then(detail => setJobDescription(detail.data.job_description || ''))
          .catch(() => {})
          .finally(() => setLoading(false));
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, [jd_id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!jobDescription.trim()) {
      setError('Please provide the job description text.');
      return;
    }

    setIsSubmitting(true);
    setError('');
    setSuccess('');
    try {
      const payload: any = {
        job_description: jobDescription,
        location,
        is_public: isPublic,
      };
      // Only send type/function when explicitly chosen (backend leaves them unchanged otherwise)
      if (jobTypeId) payload.job_type_id = jobTypeId;
      if (jobFunctionId) payload.job_function_id = jobFunctionId;
      await api.put(`/nlp/jd/${jd_id}`, payload);
      // Keep the form usable so the JD can be updated again in the same
      // session without a full reload. Previously isSubmitting stayed true
      // on success, locking the button until sign-out/in.
      setSuccess('Job Description updated successfully! You can keep editing below.');
      // Reset the "keep current" selects so an unchanged second save
      // doesn't resend stale ids.
      setJobTypeId('');
      setJobFunctionId('');
      router.push('/company/jobs');
      router.refresh();
    } catch (err: any) {
      console.error(err);
      setError(err.response?.data?.message || 'Failed to update Job Description. Please try again.');
    } finally {
      // Always re-enable the button — success or failure.
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <DashboardLayout role="COMPANY">
        <div className="max-w-3xl space-y-6 animate-pulse">
          <div className="bg-white h-16 rounded-2xl border border-gray-100" />
          <div className="bg-white h-96 rounded-2xl border border-gray-100" />
        </div>
      </DashboardLayout>
    );
  }

  if (notFound) {
    return (
      <DashboardLayout role="COMPANY">
        <div className="max-w-3xl bg-white rounded-2xl border border-gray-100 p-12 text-center">
          <h3 className="text-xl font-bold text-gray-900 mb-2">Job not found</h3>
          <p className="text-gray-500 mb-6">This job posting does not exist or belongs to another company.</p>
          <Link href="/company/jobs" className="px-6 py-2.5 bg-black text-white font-bold rounded-full hover:bg-gray-800 transition-colors">
            Back to Jobs
          </Link>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout role="COMPANY">
      <div className="max-w-3xl">
        <Link href="/company/jobs" className="inline-flex items-center gap-2 text-sm font-medium text-gray-500 hover:text-gray-900 mb-6">
          <ArrowLeft size={16} /> Back to Jobs
        </Link>
        <div className="mb-8 border-b border-gray-200 pb-6">
          <h2 className="text-3xl font-bold text-gray-900">Edit: {jdName}</h2>
          <p className="text-gray-500 mt-2">Update the description and re-run AI analysis. The job title cannot be changed.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && <div className="p-3 bg-red-50 text-red-600 rounded-lg text-sm font-medium">{error}</div>}
          {success && <div className="p-3 bg-green-50 text-green-700 rounded-lg text-sm font-medium">{success}</div>}
          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-bold text-gray-900 mb-2">Job Function <span className="font-normal text-gray-400">(unchanged if empty)</span></label>
              <select
                className="w-full bg-white border border-gray-200 rounded-lg p-3 text-gray-900 focus:ring-2 focus:ring-[#12b388] outline-none"
                value={jobFunctionId} onChange={e => setJobFunctionId(e.target.value)}
              >
                <option value="">Keep current...</option>
                {taxonomy.job_functions.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-bold text-gray-900 mb-2">Job Type <span className="font-normal text-gray-400">(unchanged if empty)</span></label>
              <select
                className="w-full bg-white border border-gray-200 rounded-lg p-3 text-gray-900 focus:ring-2 focus:ring-[#12b388] outline-none"
                value={jobTypeId} onChange={e => setJobTypeId(e.target.value)}
              >
                <option value="">Keep current...</option>
                {taxonomy.job_types.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-bold text-gray-900 mb-2">Location</label>
              <input
                type="text"
                placeholder="e.g. Remote, New York, etc."
                className="w-full bg-white border border-gray-200 rounded-lg p-3 text-gray-900 focus:ring-2 focus:ring-[#12b388] outline-none"
                value={location} onChange={e => setLocation(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-sm font-bold text-gray-900 mb-2">Visibility</label>
              <select
                className="w-full bg-white border border-gray-200 rounded-lg p-3 text-gray-900 focus:ring-2 focus:ring-[#12b388] outline-none"
                value={isPublic} onChange={e => setIsPublic(Number(e.target.value))}
              >
                <option value={1}>Public — candidates can apply</option>
                <option value={0}>Private — hidden from candidates</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">Full Job Description</label>
            <textarea
              required rows={12}
              placeholder="Paste the full updated job description here..."
              className="w-full bg-white border border-gray-200 rounded-lg p-4 text-gray-900 focus:ring-2 focus:ring-[#12b388] outline-none resize-y"
              value={jobDescription} onChange={e => setJobDescription(e.target.value)}
            />
          </div>

          <div className="pt-6">
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-8 py-3.5 bg-[#12b388] text-white font-bold rounded-lg hover:bg-[#10a078] transition-colors disabled:opacity-50 flex items-center justify-center min-w-[200px]"
            >
              {isSubmitting ? (
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              ) : (
                "Re-analyze & Save"
              )}
            </button>
          </div>
        </form>
      </div>
    </DashboardLayout>
  );
}
