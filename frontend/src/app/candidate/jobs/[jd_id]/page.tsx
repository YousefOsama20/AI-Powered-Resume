import { Suspense } from 'react';
import JobDetailClient from './client';

export const instant = false;

export default async function JobDetailPage(props: { params: Promise<{ jd_id: string }> }) {
  const params = await props.params;

  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center">Loading...</div>}>
      <JobDetailClient jd_id={params.jd_id} />
    </Suspense>
  );
}
