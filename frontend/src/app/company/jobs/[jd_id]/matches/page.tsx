import { Suspense } from 'react';
import MatchesClient from './client';

export const instant = false;

export default async function MatchesPage(props: { params: Promise<{ jd_id: string }> }) {
  const params = await props.params;
  
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center">Loading...</div>}>
      <MatchesClient jd_id={params.jd_id} />
    </Suspense>
  );
}
