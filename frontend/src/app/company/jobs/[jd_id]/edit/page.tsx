import { Suspense } from 'react';
import EditJDClient from './client';

export const instant = false;

export default async function EditJDPage(props: { params: Promise<{ jd_id: string }> }) {
  const params = await props.params;

  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center">Loading...</div>}>
      <EditJDClient jd_id={params.jd_id} />
    </Suspense>
  );
}
