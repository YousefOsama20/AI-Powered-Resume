'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import SplitScreenLayout from '@/components/SplitScreenLayout';
import api from '@/lib/axios';

export default function CompanyOnboarding() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [description, setDescription] = useState('');
  
  const handleProfileSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.put('/profile/company', {
        description
      });
      router.push('/company/dashboard');
    } catch (err) {
      console.error(err);
      alert('Failed to update company profile');
    }
  };

  return (
    <SplitScreenLayout heading="Let's set up your **Company Profile**">
      <form onSubmit={handleProfileSubmit} className="space-y-8 w-full max-w-xl mx-auto">
        
        <div>
          <label className="block text-sm font-bold text-gray-900 mb-4">* Company Description</label>
          <textarea 
            required 
            rows={6}
            className="w-full bg-gray-50 border-none rounded-lg p-4 text-gray-900 focus:ring-2 focus:ring-[#12b388] outline-none resize-none"
            placeholder="Tell us about your company, mission, and culture..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        <div className="flex justify-end mt-12">
            <button type="submit" className="px-10 py-3.5 rounded-full bg-black text-white font-medium hover:bg-gray-800 transition-colors">
                Go to Dashboard
            </button>
        </div>
      </form>
    </SplitScreenLayout>
  );
}
