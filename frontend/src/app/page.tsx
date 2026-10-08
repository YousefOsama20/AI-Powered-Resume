import Link from 'next/link';
import BrandMark from '@/components/BrandMark';

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-[#e0f7f1] to-white p-24">
      <div className="text-center space-y-6">
        <div className="flex items-center justify-center gap-2 mb-8">
            <BrandMark size={44} />
            <h1 className="text-4xl font-bold text-gray-900">
                NextHire <span className="text-emerald-500 text-lg align-top ml-1">●</span>
            </h1>
        </div>
        
        <h2 className="text-6xl font-bold text-gray-900 tracking-tight">
          Find your next big opportunity.
        </h2>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto">
          The intelligent platform connecting top talent with amazing companies through AI-powered matching.
        </p>
        <div className="flex gap-4 justify-center mt-8">
          <Link 
            href="/login" 
            className="px-8 py-3 rounded-full border-2 border-gray-900 text-gray-900 font-medium hover:bg-gray-50 transition-colors"
          >
            Login
          </Link>
          <Link 
            href="/register" 
            className="px-8 py-3 rounded-full bg-gray-900 text-white font-medium hover:bg-gray-800 transition-colors shadow-lg"
          >
            Get Started
          </Link>
        </div>
      </div>
    </main>
  );
}
