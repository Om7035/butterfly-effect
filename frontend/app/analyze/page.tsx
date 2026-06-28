"use client";

// The analyze page now redirects to the main page with the query pre-filled.
// All analysis happens on the main page (/) via the SSE stream.
import { useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";

function AnalyzeRedirect() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const q = searchParams.get("q");

  useEffect(() => {
    // Redirect to home — the main page handles all analysis
    if (q) {
      router.replace(`/?q=${encodeURIComponent(q)}`);
    } else {
      router.replace("/");
    }
  }, [q, router]);

  return (
    <div style={{ width: "100vw", height: "100vh", background: "#0a0e1a", display: "flex", alignItems: "center", justifyContent: "center", color: "#475569", fontFamily: "system-ui" }}>
      Loading...
    </div>
  );
}

export default function AnalyzePage() {
  return (
    <Suspense fallback={<div style={{ width: "100vw", height: "100vh", background: "#0a0e1a" }} />}>
      <AnalyzeRedirect />
    </Suspense>
  );
}
