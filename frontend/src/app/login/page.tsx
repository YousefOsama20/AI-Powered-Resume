'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import SplitScreenLayout from '@/components/SplitScreenLayout';
import api from '@/lib/axios';

export default function Login() {
  const router = useRouter();
  const [formData, setFormData] = useState({ email: '', password: '' });
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const res = await api.post('/auth/login', formData);
      localStorage.setItem('access_token', res.data.access_token);
      
      // Determine where to send them based on their profile data
      // For now, let's just attempt to fetch the profile to see role
      try {
        await api.get('/data/customer/documents');
        router.push('/candidate/dashboard');
      } catch {
        router.push('/company/dashboard');
      }

    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid credentials');
    }
  };

  return (
    <SplitScreenLayout heading="Welcome back to **NextHire**">
      <form onSubmit={handleSubmit} className="space-y-6 w-full max-w-md mx-auto">
        {error && <div className="p-3 bg-red-50 text-red-500 rounded-lg text-sm">{error}</div>}
        
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

        <div className="flex justify-end mt-12">
            <button type="submit" className="px-10 py-3.5 rounded-full bg-black text-white font-medium hover:bg-gray-800 transition-colors">
                Login
            </button>
        </div>
      </form>
    </SplitScreenLayout>
  );
}
