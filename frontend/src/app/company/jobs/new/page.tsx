'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import DashboardLayout from '@/components/DashboardLayout';
import api from '@/lib/axios';

export default function CreateJD() {
  const router = useRouter();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [taxonomy, setTaxonomy] = useState<{job_types: any[], job_functions: any[]}>({ job_types: [], job_functions: [] });
  
  const [formData, setFormData] = useState({
    jd_name: '',
    location: '',
    job_type_id: '',
    job_function_id: '',
    job_description: '',
    is_public: 1
  });
  const [requiredExperience, setRequiredExperience] = useState('0');

  useEffect(() => {
    api.get('/profile/taxonomy').then(res => setTaxonomy(res.data)).catch(console.error);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.job_type_id || !formData.job_function_id) return alert('Please select Job Type and Function.');
    
    setIsSubmitting(true);
    try {
      await api.post('/nlp/jd', formData);
      alert('Job Description successfully analyzed and posted!');
      router.push('/company/dashboard');
    } catch (err) {
      console.error(err);
      alert('Failed to post Job Description');
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
