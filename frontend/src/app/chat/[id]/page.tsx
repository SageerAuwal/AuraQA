import ChatClient from "./ChatClient";

export async function generateStaticParams() {
  // Return a list containing a dummy ID to satisfy the Next.js static compiler at build time.
  // Dynamic runtime chats will be resolved on the client using single-page routing fallbacks.
  return [{ id: "1" }];
}

interface ChatPageProps {
  params: Promise<{ id: string }>;
}

export default function ChatPage({ params }: ChatPageProps) {
  return <ChatClient params={params} />;
}
