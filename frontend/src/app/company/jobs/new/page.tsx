'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import DashboardLayout from '@/components/DashboardLayout';
import api from '@/lib/axios';

export default function CreateJD() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [taxonomy, setTaxonomy] = useState<{job_types: any[], job_functions: any[]}>({ job_types: [], job_functions: [] });

  const initialForm = {
    jd_name: '',
    location: '',
    job_type_id: '',
    job_function_id: '',
    job_description: '',
    is_public: 1
  };
  const [formData, setFormData] = useState(initialForm);
  const [requiredExperience, setRequiredExperience] = useState('0');

  useEffect(() => {
    api.get('/profile/taxonomy').then(res => setTaxonomy(res.data)).catch(console.error);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.job_type_id || !formData.job_function_id) {
      setError('Please select Job Type and Function.');
      return;
    }

    setIsSubmitting(true);
    setError('');
    setSuccess('');
    try {
      const payload = {
        ...formData,
        jd_name: formData.jd_name.trim(),
        required_experience: requiredExperience === '' ? null : Number(requiredExperience),
      };
      await api.post('/nlp/jd', payload);
      // Clear the form so a second JD can be posted immediately without
      // a full reload. Previously stale state + a stuck isSubmitting flag
      // forced users to sign out/in to post again.
      setFormData(initialForm);
      setRequiredExperience('0');
      setSuccess('Job Description successfully analyzed and posted! You can post another one below.');
      router.push('/company/jobs');
      router.refresh();
    } catch (err: any) {
      console.error(err);
      const status = err.response?.status;
      const serverMsg = err.response?.data?.message;
      if (status === 409) {
        setError(serverMsg || 'A job with this title already exists. Please use a different title or edit the existing one.');
      } else {
        setError(serverMsg || 'Failed to post Job Description. Please try again.');
      }
    } finally {
      // Always re-enable the button — success or failure — so consecutive
      // JD posts work in the same session.
      setIsSubmitting(false);
    }
  };

  return (
    <DashboardLayout role="COMPANY">
      <div className="max-w-3xl">
        <div className="mb-8 border-b border-gray-200 pb-6">
          <h2 className="text-3xl font-bold text-gray-900">Create New Job Posting</h2>
          <p className="text-gray-500 mt-2">Our AI will automatically analyze your description to extract essential skills and match top candidates.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {error && <div className="p-3 bg-red-50 text-red-600 rounded-lg text-sm font-medium">{error}</div>}
          {success && <div className="p-3 bg-green-50 text-green-700 rounded-lg text-sm font-medium">{success}</div>}
          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-bold text-gray-900 mb-2">Job Title</label>
              <input 
                type="text" required
                placeholder="e.g. Senior Frontend Engineer"
                className="w-full bg-white border border-gray-200 rounded-lg p-3 text-gray-900 focus:ring-2 focus:ring-[#12b388] outline-none"
                value={formData.jd_name} onChange={e => setFormData({...formData, jd_name: e.target.value})}
              />
            </div>
            <div>
              <label className="block text-sm font-bold text-gray-900 mb-2">Required Experience (Years)</label>
              <input 
                type="number" required min="0" step="0.5"
                placeholder="e.g. 3.5"
                className="w-full bg-white border border-gray-200 rounded-lg p-3 text-gray-900 focus:ring-2 focus:ring-[#12b388] outline-none"
                value={requiredExperience} onChange={e => setRequiredExperience(e.target.value)}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-bold text-gray-900 mb-2">Job Function</label>
              <select 
                required
                className="w-full bg-white border border-gray-200 rounded-lg p-3 text-gray-900 focus:ring-2 focus:ring-[#12b388] outline-none"
                value={formData.job_function_id} onChange={e => setFormData({...formData, job_function_id: e.target.value})}
              >
                <option value="" disabled>Select Function...</option>
                {taxonomy.job_functions.map(f => <option key={f.id} value={f.id}>{f.name}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-bold text-gray-900 mb-2">Job Type</label>
              <select 
                required
                className="w-full bg-white border border-gray-200 rounded-lg p-3 text-gray-900 focus:ring-2 focus:ring-[#12b388] outline-none"
                value={formData.job_type_id} onChange={e => setFormData({...formData, job_type_id: e.target.value})}
              >
                <option value="" disabled>Select Type...</option>
                {taxonomy.job_types.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">Location</label>
            <input 
              type="text" required
              placeholder="e.g. Remote, New York, etc."
              className="w-full bg-white border border-gray-200 rounded-lg p-3 text-gray-900 focus:ring-2 focus:ring-[#12b388] outline-none"
              value={formData.location} onChange={e => setFormData({...formData, location: e.target.value})}
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-gray-900 mb-2">Full Job Description</label>
            <textarea 
              required rows={12}
              placeholder="Paste the full job description here..."
              className="w-full bg-white border border-gray-200 rounded-lg p-4 text-gray-900 focus:ring-2 focus:ring-[#12b388] outline-none resize-y"
              value={formData.job_description} onChange={e => setFormData({...formData, job_description: e.target.value})}
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
                "Analyze & Post Job"
              )}
            </button>
          </div>
        </form>
      </div>
    </DashboardLayout>
  );
}
