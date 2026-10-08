'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import SplitScreenLayout from '@/components/SplitScreenLayout';
import api from '@/lib/axios';

export default function Register() {
  const router = useRouter();
  const [role, setRole] = useState<'CUSTOMER' | 'COMPANY' | null>(null);
  const [formData, setFormData] = useState({ name: '', email: '', password: '' });
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.post('/auth/register', { ...formData, role });
      // After registration, login automatically
      const res = await api.post('/auth/login', { email: formData.email, password: formData.password });
      localStorage.setItem('access_token', res.data.access_token);
      
      // Redirect to onboarding
      if (role === 'CUSTOMER') router.push('/candidate/onboarding');
      else router.push('/company/onboarding');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed');
    }
  };

  if (!role) {
    return (
      <SplitScreenLayout heading="To get started, **who are you**?">
        <div className="space-y-6">
          <div className="flex gap-4">
            <button 
              onClick={() => setRole('CUSTOMER')}
              className="flex-1 p-6 border-2 border-gray-100 rounded-xl hover:border-[#12b388] hover:bg-[#12b388]/5 transition-all text-left group"
            >
              <h3 className="text-xl font-bold text-gray-900 group-hover:text-[#12b388]">Candidate</h3>
              <p className="text-sm text-gray-500 mt-2">I am looking for a job and want to upload my CV.</p>
            </button>
            <button 
              onClick={() => setRole('COMPANY')}
              className="flex-1 p-6 border-2 border-gray-100 rounded-xl hover:border-[#12b388] hover:bg-[#12b388]/5 transition-all text-left group"
            >
              <h3 className="text-xl font-bold text-gray-900 group-hover:text-[#12b388]">Company</h3>
              <p className="text-sm text-gray-500 mt-2">I am hiring and want to post Job Descriptions.</p>
            </button>
          </div>
        </div>
      </SplitScreenLayout>
    );
  }

  return (
    <SplitScreenLayout heading="Just a few details to **create your account**">
      <form onSubmit={handleSubmit} className="space-y-6 w-full max-w-md mx-auto">
        {error && <div className="p-3 bg-red-50 text-red-500 rounded-lg text-sm">{error}</div>}
        
        <div>
          <label className="block text-sm font-semibold text-gray-900 mb-2">Full Name</label>
          <input 
            type="text" 
            required 
            className="w-full bg-gray-50 border-none rounded-lg p-4 text-gray-900 focus:ring-2 focus:ring-[#12b388] outline-none"
            placeholder={role === 'COMPANY' ? "Company Name" : "John Doe"}
            value={formData.name}
            onChange={(e) => setFormData({...formData, name: e.target.value})}
          />
        </div>
        
        <div>
          <label className="block text-sm font-semibold text-gray-900 mb-2">Email</label>
          <input 
            type="email" 
            required 
            className="w-full bg-gray-50 border-none rounded-lg p-4 text-gray-900 focus:ring-2 focus:ring-[#12b388] outline-none"
            placeholder="john@example.com"
            value={formData.email}
            onChange={(e) => setFormData({...formData, email: e.target.value})}
          />
        </div>

        <div>
          <label className="block text-sm font-semibold text-gray-900 mb-2">Password</label>
          <input 
            type="password" 
            required 
            className="w-full bg-gray-50 border-none rounded-lg p-4 text-gray-900 focus:ring-2 focus:ring-[#12b388] outline-none"
            placeholder="••••••••"
            value={formData.password}
            onChange={(e) => setFormData({...formData, password: e.target.value})}
          />
        </div>

        <div className="flex justify-between items-center mt-12">
            <button type="button" onClick={() => setRole(null)} className="text-gray-500 font-medium hover:text-gray-900">
                Back
            </button>
            <button type="submit" className="px-10 py-3.5 rounded-full bg-black text-white font-medium hover:bg-gray-800 transition-colors">
                Next
            </button>
        </div>
      </form>
    </SplitScreenLayout>
  );
}
