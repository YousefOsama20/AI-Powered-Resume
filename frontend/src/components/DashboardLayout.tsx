'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Briefcase, FileText, User, MessageSquare, Settings } from 'lucide-react';

interface DashboardLayoutProps {
  children: React.ReactNode;
  role: 'CANDIDATE' | 'COMPANY';
}

export default function DashboardLayout({ children, role }: DashboardLayoutProps) {
  const pathname = usePathname();
  const basePath = role === 'CANDIDATE' ? '/candidate' : '/company';

  const navItems = role === 'CANDIDATE' ? [
    { name: 'Jobs', icon: Briefcase, path: `${basePath}/dashboard` },
    { name: 'Resume', icon: FileText, path: `${basePath}/resumes` },
    { name: 'Profile', icon: User, path: `${basePath}/profile` },
    { name: 'Applications', icon: MessageSquare, path: `${basePath}/applications` },
    { name: 'Settings', icon: Settings, path: '/settings' },
  ] : [
    { name: 'Dashboard', icon: Briefcase, path: `${basePath}/dashboard` },
    { name: 'Jobs', icon: FileText, path: `${basePath}/jobs` },
    { name: 'Profile', icon: User, path: `${basePath}/profile` },
    { name: 'Settings', icon: Settings, path: '/settings' },
  ];

  return (
    <div className="flex min-h-screen bg-[#f8fafc]">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-100 flex flex-col fixed h-full z-10">
        <div className="p-6 flex items-center gap-2 mb-4">
            <div className="w-8 h-8 rounded-full bg-[#12b388] flex items-center justify-center text-white font-bold text-sm relative">
                <div className="absolute top-2 left-2 w-1 h-1 bg-black rounded-full" />
                <div className="absolute top-2 right-2 w-1 h-1 bg-black rounded-full" />
                <div className="absolute bottom-2 w-3 h-0.5 bg-black rounded-full" />
            </div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight leading-none">
                Jobright <span className="text-[#12b388]">●</span>
            </h1>
        </div>
        
        <nav className="flex-1 px-4 space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.path;
            const Icon = item.icon;
            return (
              <Link
                key={item.name}
                href={item.path}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-colors ${
                  isActive 
                    ? 'bg-[#12b388]/10 text-[#12b388]' 
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                }`}
              >
                <Icon size={18} className={isActive ? 'text-[#12b388]' : 'text-gray-400'} />
                {item.name}
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Main Content */}
      <main className="flex-1 ml-64 p-8 flex flex-col min-h-screen">
        {children}
      </main>
    </div>
  );
}
