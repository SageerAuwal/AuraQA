import StudyClient from "./StudyClient";

export async function generateStaticParams() {
  // Return a list containing a dummy ID to satisfy the Next.js static compiler at build time.
  // Dynamic runtime study sessions will be resolved on the client using single-page routing fallbacks.
  return [{ id: "1" }];
}

interface StudyPageProps {
  params: Promise<{ id: string }>;
}

export default function StudyDashboardPage({ params }: StudyPageProps) {
  return <StudyClient params={params} />;
}
