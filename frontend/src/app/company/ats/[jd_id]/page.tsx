import { Suspense } from 'react';
import ATSClient from './client';

export const instant = false;

export default async function ATSBoardPage(props: { params: Promise<{ jd_id: string }> }) {
  const params = await props.params;
  
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center">Loading...</div>}>
      <ATSClient jd_id={params.jd_id} />
    </Suspense>
  );
}
