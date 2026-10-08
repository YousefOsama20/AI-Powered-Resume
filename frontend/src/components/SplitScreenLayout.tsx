import React from 'react';
import Link from 'next/link';
import BrandMark from '@/components/BrandMark';

interface SplitScreenLayoutProps {
  children: React.ReactNode;
  heading: string;
}

export default function SplitScreenLayout({ children, heading }: SplitScreenLayoutProps) {
  return (
    <div className="flex min-h-screen bg-white">
      {/* Left side - Fixed Gradient */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-[#d4fce8] to-[#e0fcfb] flex-col p-16 fixed h-full border-r border-gray-100 shadow-sm">
        <div className="flex items-center gap-2 mb-32">
            <BrandMark size={40} />
            <div>
              <h1 className="text-xl font-bold text-gray-900 tracking-tight leading-none">
                  NextHire <span className="text-[#12b388]">●</span>
              </h1>
              <span className="text-xs text-gray-500 font-medium tracking-wide">Your NextHire AI Copilot</span>
            </div>
        </div>
        
        <h2 className="text-[2.75rem] font-medium text-gray-900 leading-[1.1] max-w-md tracking-tight">
          {heading.split(/(\*\*.*?\*\*)/).map((part, i) => {
            if (part.startsWith('**') && part.endsWith('**')) {
              return <span key={i} className="font-bold">{part.slice(2, -2)}</span>;
            }
            return part;
          })}
        </h2>
      </div>

      {/* Right side - Scrollable Content */}
      <div className="w-full lg:w-1/2 lg:ml-[50%] flex flex-col min-h-screen bg-white relative">
        <div className="absolute top-8 right-8">
            <Link href="/login" className="text-sm font-medium text-gray-500 hover:text-gray-900 border border-gray-200 rounded-full px-4 py-1.5 transition-colors">
                Logout
            </Link>
        </div>
        <div className="flex-1 flex flex-col justify-center max-w-2xl w-full mx-auto p-16">
            {children}
        </div>
      </div>
    </div>
  );
}
