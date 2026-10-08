'use client';

import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import AvatarUpload from '@/components/AvatarUpload';
import api from '@/lib/axios';

export default function CompanyProfile() {
  const [companyName, setCompanyName] = useState('');
  const [description, setDescription] = useState('');
  const [website, setWebsite] = useState('');
  const [industry, setIndustry] = useState('');
  const [location, setLocation] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const [photoVersion, setPhotoVersion] = useState(0);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);

  useEffect(() => {
    api.get('/profile/company')
      .then(res => {
        const data = res.data;
        setCompanyName(data.company_name || '');
        setDescription(data.description || '');
        setWebsite(data.website || '');
        setIndustry(data.industry || '');
        setLocation(data.location || '');
        setPhotoUrl(data.photo_url || null);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const handlePhotoUpload = async (file: File) => {
    setUploadingPhoto(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api.post('/profile/company/photo', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setPhotoUrl(res.data.photo_url || '/profile/company/photo');
      setPhotoVersion((v) => v + 1);
    } catch (err) {
      console.error(err);
      alert('Failed to upload photo. Use JPG, PNG or WebP under 5MB.');
    }
    setUploadingPhoto(false);
  };

  const handlePhotoRemove = async () => {
    try {
      await api.delete('/profile/company/photo');
      setPhotoUrl(null);
      setPhotoVersion((v) => v + 1);
    } catch (err) {
      console.error(err);
      alert('Failed to remove photo');
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await api.put('/profile/company', {
        company_name: companyName,
        description,
        website,
        industry,
        location,
      });
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      console.error(err);
      alert('Failed to save profile');
    }
    setSaving(false);
  };

  return (
    <DashboardLayout role="COMPANY">
      <div className="max-w-2xl">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900">Company Profile</h2>
          <p className="text-gray-500 mt-2">Update your company information to attract the right candidates.</p>
        </div>

        {loading ? (
          <div className="bg-white rounded-2xl border border-gray-100 p-6 space-y-6 animate-pulse">
            <div className="h-10 bg-gray-100 rounded-lg" />
            <div className="h-32 bg-gray-100 rounded-lg" />
            <div className="h-10 bg-gray-100 rounded-lg" />
          </div>
        ) : (
          <form onSubmit={handleSave} className="space-y-6">
            <div className="bg-white rounded-2xl border border-gray-100 p-6 space-y-6">
              <h3 className="text-lg font-bold text-gray-900 border-b border-gray-100 pb-4">Company Logo</h3>
              <AvatarUpload
                photoUrl={photoUrl ? `${photoUrl}?v=${photoVersion}` : null}
                fallbackLabel={companyName || 'Company'}
                uploading={uploadingPhoto}
                onUpload={handlePhotoUpload}
                onRemove={handlePhotoRemove}
              />
            </div>

            <div className="bg-white rounded-2xl border border-gray-100 p-6 space-y-6">
              <h3 className="text-lg font-bold text-gray-900 border-b border-gray-100 pb-4">About Your Company</h3>
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Company Name</label>
                <input
                  type="text"
                  placeholder="e.g. Tech Corp"
                  className="w-full bg-gray-50 border-none rounded-lg p-3 text-gray-900 focus:ring-2 focus:ring-[#12b388] outline-none"
                  value={companyName} onChange={e => setCompanyName(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Company Description</label>
                <textarea
                  rows={8}
                  placeholder="Tell candidates about your company, mission, culture, and what makes you unique..."
                  className="w-full bg-gray-50 border-none rounded-lg p-4 text-gray-900 focus:ring-2 focus:ring-[#12b388] outline-none resize-y"
                  value={description} onChange={e => setDescription(e.target.value)}
                />
              </div>
              <div className="grid grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm font-bold text-gray-900 mb-2">Website</label>
                  <input
                    type="url"
                    placeholder="https://example.com"
                    className="w-full bg-gray-50 border-none rounded-lg p-3 text-gray-900 focus:ring-2 focus:ring-[#12b388] outline-none"
                    value={website} onChange={e => setWebsite(e.target.value)}
                  />
                </div>
                <div>
                  <label className="block text-sm font-bold text-gray-900 mb-2">Industry</label>
                  <input
                    type="text"
                    placeholder="e.g. Software, Fintech, Healthcare"
                    className="w-full bg-gray-50 border-none rounded-lg p-3 text-gray-900 focus:ring-2 focus:ring-[#12b388] outline-none"
                    value={industry} onChange={e => setIndustry(e.target.value)}
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Location</label>
                <input
                  type="text"
                  placeholder="e.g. New York, NY / Remote"
                  className="w-full bg-gray-50 border-none rounded-lg p-3 text-gray-900 focus:ring-2 focus:ring-[#12b388] outline-none"
                  value={location} onChange={e => setLocation(e.target.value)}
                />
              </div>
            </div>

            <div className="flex items-center gap-4">
              <button
                type="submit" disabled={saving}
                className="px-8 py-3 bg-black text-white font-bold rounded-full hover:bg-gray-800 transition-colors disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
              {saved && <span className="text-[#12b388] font-medium text-sm animate-pulse">✓ Profile saved successfully!</span>}
            </div>
          </form>
        )}
      </div>
    </DashboardLayout>
  );
}
