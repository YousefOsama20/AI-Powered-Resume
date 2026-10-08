'use client';

import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import MultiSelectDropdown from '@/components/MultiSelectDropdown';
import AvatarUpload from '@/components/AvatarUpload';
import api from '@/lib/axios';

export default function CandidateProfile() {
  const [taxonomy, setTaxonomy] = useState<{job_types: any[], job_functions: any[]}>({ job_types: [], job_functions: [] });
  const [location, setLocation] = useState('');
  const [phone, setPhone] = useState('');
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [selectedFunctions, setSelectedFunctions] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);
  const [photoVersion, setPhotoVersion] = useState(0);
  const [uploadingPhoto, setUploadingPhoto] = useState(false);

  useEffect(() => {
    api.get('/profile/taxonomy').then(res => setTaxonomy(res.data)).catch(console.error);
    api.get('/profile/customer')
      .then(res => {
        const data = res.data;
        setPhone(data.phone || '');
        setLocation(data.location || '');
        setPhotoUrl(data.photo_url || null);
        setSelectedTypes((data.job_types || []).map((t: any) => t.id));
        setSelectedFunctions((data.job_functions || []).map((f: any) => f.id));
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setLoading(false);
      });
  }, []);

  const toggleType = (id: string) => {
    setSelectedTypes(prev => prev.includes(id) ? prev.filter(t => t !== id) : [...prev, id]);
  };

  const toggleFunction = (id: string) => {
    setSelectedFunctions(prev => prev.includes(id) ? prev.filter(f => f !== id) : [...prev, id]);
  };

  const handlePhotoUpload = async (file: File) => {
    setUploadingPhoto(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await api.post('/profile/customer/photo', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setPhotoUrl(res.data.photo_url || '/profile/customer/photo');
      setPhotoVersion((v) => v + 1);
    } catch (err) {
      console.error(err);
      alert('Failed to upload photo. Use JPG, PNG or WebP under 5MB.');
    }
    setUploadingPhoto(false);
  };

  const handlePhotoRemove = async () => {
    try {
      await api.delete('/profile/customer/photo');
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
      await api.put('/profile/customer', {
        phone,
        location,
        job_type_ids: selectedTypes,
        job_function_ids: selectedFunctions
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
    <DashboardLayout role="CANDIDATE">
      <div className="max-w-2xl">
        <div className="mb-8">
          <h2 className="text-3xl font-bold text-gray-900">Your Profile</h2>
          <p className="text-gray-500 mt-2">Keep your preferences up to date for better job recommendations.</p>
        </div>

        {loading ? (
          <div className="bg-white rounded-2xl border border-gray-100 p-6 space-y-6 animate-pulse">
            <div className="h-10 bg-gray-100 rounded-lg" />
            <div className="h-10 bg-gray-100 rounded-lg" />
            <div className="h-24 bg-gray-100 rounded-lg" />
          </div>
        ) : (
        <form onSubmit={handleSave} className="space-y-8">
          <div className="bg-white rounded-2xl border border-gray-100 p-6 space-y-6">
            <h3 className="text-lg font-bold text-gray-900 border-b border-gray-100 pb-4">Profile Photo</h3>
            <AvatarUpload
              photoUrl={photoUrl ? `${photoUrl}?v=${photoVersion}` : null}
              fallbackLabel="Candidate"
              uploading={uploadingPhoto}
              onUpload={handlePhotoUpload}
              onRemove={handlePhotoRemove}
            />
          </div>

          <div className="bg-white rounded-2xl border border-gray-100 p-6 space-y-6">
            <h3 className="text-lg font-bold text-gray-900 border-b border-gray-100 pb-4">Personal Information</h3>
            <div className="grid grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Phone</label>
                <input
                  type="tel"
                  placeholder="+1 555 123 4567"
                  className="w-full bg-gray-50 border-none rounded-lg p-3 text-gray-900 focus:ring-2 focus:ring-[#12b388] outline-none"
                  value={phone} onChange={e => setPhone(e.target.value)}
                />
              </div>
              <div>
                <label className="block text-sm font-bold text-gray-900 mb-2">Location</label>
                <input
                  type="text"
                  placeholder="New York, NY"
                  className="w-full bg-gray-50 border-none rounded-lg p-3 text-gray-900 focus:ring-2 focus:ring-[#12b388] outline-none"
                  value={location} onChange={e => setLocation(e.target.value)}
                />
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-gray-100 p-6 space-y-6">
            <h3 className="text-lg font-bold text-gray-900 border-b border-gray-100 pb-4">Job Preferences</h3>
            <div>
              <label className="block text-sm font-bold text-gray-900 mb-3">Preferred Job Functions</label>
              <MultiSelectDropdown
                options={taxonomy.job_functions}
                selected={selectedFunctions}
                onToggle={toggleFunction}
                onClear={() => setSelectedFunctions([])}
                placeholder="Select job functions"
              />
            </div>
            <div>
              <label className="block text-sm font-bold text-gray-900 mb-3">Preferred Job Types</label>
              <div className="grid grid-cols-2 gap-3">
                {taxonomy.job_types.map(type => (
                  <button
                    type="button" key={type.id}
                    onClick={() => toggleType(type.id)}
                    className={`flex items-center gap-3 p-3 rounded-lg text-sm font-medium transition-colors ${selectedTypes.includes(type.id) ? 'bg-[#12b388]/10 text-[#12b388]' : 'bg-gray-50 text-gray-700 hover:bg-gray-100'}`}
                  >
                    <div className={`w-5 h-5 rounded flex items-center justify-center ${selectedTypes.includes(type.id) ? 'bg-[#12b388] text-white' : 'bg-gray-200'}`}>
                      {selectedTypes.includes(type.id) && '✓'}
                    </div>
                    {type.name}
                  </button>
                ))}
              </div>
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
