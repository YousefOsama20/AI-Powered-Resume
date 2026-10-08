'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import SplitScreenLayout from '@/components/SplitScreenLayout';
import MultiSelectDropdown from '@/components/MultiSelectDropdown';
import api from '@/lib/axios';

export default function CandidateOnboarding() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [taxonomy, setTaxonomy] = useState<{job_types: any[], job_functions: any[]}>({ job_types: [], job_functions: [] });
  
  // Profile Data
  const [location, setLocation] = useState('Anywhere in the US');
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [selectedFunctions, setSelectedFunctions] = useState<string[]>([]);
  
  // File Upload Data
  const [file, setFile] = useState<File | null>(null);

  useEffect(() => {
    api.get('/profile/taxonomy').then(res => setTaxonomy(res.data)).catch(console.error);
  }, []);

  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedFunctions.length === 0 || selectedTypes.length === 0) return alert('Please select at least one job function and at least one job type.');
    try {
      await api.put('/profile/customer', {
        location,
        job_type_ids: selectedTypes,
        job_function_ids: selectedFunctions
      });
      setStep(2);
    } catch (err) {
      console.error(err);
      alert('Failed to update profile');
    }
  };

  const handleFileUpload = async () => {
    if (!file) return alert('Please select a file');
    setStep(3); // Scanning step
    
    try {
      // 1. Upload
      const formData = new FormData();
      formData.append('file', file);
      const uploadRes = await api.post('/data/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      const fileId = uploadRes.data.file_id;

      // 2. Index & Process
      await api.post('/nlp/index', { file_id: fileId });

      // 3. Done!
      router.push('/candidate/dashboard');
    } catch (err) {
      console.error(err);
      alert('Failed to process CV. Please try again.');
      setStep(2);
    }
  };

  const toggleType = (id: string) => {
    setSelectedTypes(prev => prev.includes(id) ? prev.filter(t => t !== id) : [...prev, id]);
  };

  const toggleFunction = (id: string) => {
    setSelectedFunctions(prev => prev.includes(id) ? prev.filter(f => f !== id) : [...prev, id]);
  };

  if (step === 1) {
    return (
      <SplitScreenLayout heading="To get started, **what type of role** are you looking for?">
        <form onSubmit={handleProfileSubmit} className="space-y-8 w-full max-w-xl mx-auto">
          
          <div>
            <label className="block text-sm font-bold text-gray-900 mb-4">* Job Function <span className="font-normal text-gray-400">(select as many as you like)</span></label>
            <MultiSelectDropdown
              options={taxonomy.job_functions}
              selected={selectedFunctions}
              onToggle={toggleFunction}
              onClear={() => setSelectedFunctions([])}
              placeholder="Please select your expected job functions"
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-gray-900 mb-4">* Job Type</label>
            <div className="grid grid-cols-2 gap-3">
              {taxonomy.job_types.map(type => (
                <button
                  type="button"
                  key={type.id}
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

          <div>
            <label className="block text-sm font-bold text-gray-900 mb-4">* Location</label>
            <input 
              type="text" 
              required 
              className="w-full bg-gray-50 border-none rounded-lg p-4 text-gray-900 focus:ring-2 focus:ring-[#12b388] outline-none"
              placeholder="Anywhere in the US"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
            />
          </div>

          <div className="flex justify-end mt-12">
              <button type="submit" className="px-10 py-3.5 rounded-full bg-black text-white font-medium hover:bg-gray-800 transition-colors">
                  Next
              </button>
          </div>
        </form>
      </SplitScreenLayout>
    );
  }

  if (step === 2) {
    return (
      <SplitScreenLayout heading="One last step, let's level up your search by **uploading your resume**">
        <div className="w-full max-w-xl mx-auto flex flex-col items-center text-center">
          
          <div className="w-32 h-32 bg-gray-50 rounded-full flex items-center justify-center mb-8 relative border-2 border-dashed border-gray-200">
            <svg className="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
            <div className="absolute -bottom-2 -right-2 bg-black text-white p-2 rounded-xl">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
            </div>
          </div>

          <input 
            type="file" 
            id="resume-upload" 
            className="hidden" 
            accept=".pdf,.doc,.docx"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
          <label 
            htmlFor="resume-upload" 
            className="px-8 py-4 rounded-full border-2 border-gray-200 text-gray-900 font-medium hover:border-[#12b388] cursor-pointer transition-colors mb-4 w-full max-w-sm block text-center"
          >
            {file ? file.name : "Upload Your Resume"}
          </label>
          <p className="text-xs text-gray-500 mb-12">Files should be in PDF or Word format and must not exceed 10MB in size.</p>

          <div className="bg-[#12b388]/10 p-4 rounded-xl text-xs text-[#12b388] max-w-md font-medium">
            Data privacy is the top priority at Jobright. Your resume will only be used for job matching and will never be shared with third parties.
          </div>

          <div className="flex justify-center mt-12 w-full">
              <button 
                onClick={handleFileUpload}
                disabled={!file}
                className="px-10 py-3.5 rounded-full bg-[#12b388] text-white font-bold hover:bg-[#10a078] disabled:opacity-50 transition-colors w-64"
              >
                  Start Matching
              </button>
          </div>
        </div>
      </SplitScreenLayout>
    );
  }

  // Step 3: Scanning
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-white">
      <div className="w-32 h-32 bg-gray-50 rounded-2xl flex items-center justify-center mb-12 relative overflow-hidden">
        <svg className="w-12 h-12 text-gray-400 relative z-10" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
        <div className="absolute top-0 left-0 w-full h-1 bg-[#12b388] shadow-[0_0_15px_#12b388] animate-[bounce_2s_infinite]"></div>
      </div>
      <div className="w-64 h-1.5 bg-gray-100 rounded-full overflow-hidden mb-8 relative">
        <div className="h-full bg-[#12b388] w-1/2 rounded-full absolute animate-[ping_2s_ease-in-out_infinite]"></div>
      </div>
      <h2 className="text-xl font-medium text-gray-900">Scanning your resume for key skills, work history, and education.</h2>
    </div>
  );
}
