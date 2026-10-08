'use client';

import { useState, useEffect } from 'react';
import DashboardLayout from '@/components/DashboardLayout';
import api from '@/lib/axios';
import { FileText, Trash2, Upload, Star } from 'lucide-react';

export default function CandidateResumes() {
  const [documents, setDocuments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  const fetchDocuments = async () => {
    try {
      const res = await api.get('/data/customer/documents');
      setDocuments(res.data.documents || []);
    } catch (err) {
      console.error(err);
    }
    setLoading(false);
  };

  useEffect(() => { fetchDocuments(); }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const uploadRes = await api.post('/data/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      const fileId = uploadRes.data.file_id;
      await api.post('/nlp/index', { file_id: fileId });
      alert('Resume uploaded and indexed successfully!');
      fetchDocuments();
    } catch (err) {
      console.error(err);
      alert('Failed to upload resume.');
    }
    setUploading(false);
  };

  const handleDelete = async (documentId: string) => {
    if (!confirm('Are you sure you want to delete this resume?')) return;
    try {
      await api.delete(`/data/customer/documents/${documentId}`);
      setDocuments(prev => prev.filter(d => d.id !== documentId));
    } catch (err) {
      console.error(err);
      alert('Failed to delete resume.');
    }
  };

  const handleDownload = async () => {
    try {
      const res = await api.get('/data/download/me', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'my_resume.pdf');
      document.body.appendChild(link);
      link.click();
    } catch (err) {
      alert('Failed to download resume.');
    }
  };

  return (
    <DashboardLayout role="CANDIDATE">
      <div className="max-w-3xl">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-3xl font-bold text-gray-900">Your Resumes</h2>
            <p className="text-gray-500 mt-2">Manage your uploaded CVs. Upload new ones to improve your match accuracy.</p>
          </div>
          <div>
            <input type="file" id="cv-upload" className="hidden" accept=".pdf,.doc,.docx" onChange={handleUpload} />
            <label
              htmlFor="cv-upload"
              className={`flex items-center gap-2 px-6 py-2.5 bg-black text-white font-medium rounded-full hover:bg-gray-800 transition-colors cursor-pointer ${uploading ? 'opacity-50 pointer-events-none' : ''}`}
            >
              <Upload size={16} />
              {uploading ? 'Uploading...' : 'Upload New CV'}
            </label>
          </div>
        </div>

        <div className="space-y-4">
          {loading ? (
            [1, 2].map(i => <div key={i} className="bg-white h-24 rounded-2xl border border-gray-100 animate-pulse" />)
          ) : documents.length === 0 ? (
            <div className="bg-white rounded-2xl border border-gray-100 p-12 text-center">
              <FileText size={48} className="text-gray-300 mx-auto mb-4" />
              <h3 className="text-xl font-bold text-gray-900 mb-2">No resumes uploaded</h3>
              <p className="text-gray-500">Upload your first resume to start getting matched with jobs.</p>
            </div>
          ) : (
            documents.map(doc => (
              <div key={doc.id} className="bg-white rounded-2xl border border-gray-100 p-6 flex items-center justify-between hover:shadow-sm transition-shadow">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-xl bg-[#12b388]/10 flex items-center justify-center">
                    <FileText size={24} className="text-[#12b388]" />
                  </div>
                  <div>
                    <h4 className="font-bold text-gray-900">{doc.file_name || doc.id}</h4>
                    <p className="text-xs text-gray-500 mt-1">
                      Uploaded: {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : 'N/A'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <button onClick={handleDownload} className="px-4 py-2 text-sm font-medium border border-gray-200 rounded-lg text-gray-700 hover:bg-gray-50 transition-colors">
                    Download
                  </button>
                  <button onClick={() => handleDelete(doc.id)} className="p-2 text-red-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors">
                    <Trash2 size={18} />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
