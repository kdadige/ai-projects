import Link from "next/link";

export default function NotFound() {
  return (
    <main className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
      <div className="max-w-md w-full bg-white border border-slate-200 rounded-2xl p-8 text-center shadow-sm">
        <p className="text-sm font-semibold text-slate-500">404</p>
        <h1 className="mt-2 text-2xl font-bold text-slate-800">Page not found</h1>
        <p className="mt-2 text-sm text-slate-600">
          The page you requested does not exist or may have moved.
        </p>
        <div className="mt-6 flex gap-3 justify-center">
          <Link
            href="/login"
            className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700"
          >
            Go to Login
          </Link>
          <Link
            href="/chat"
            className="px-4 py-2 rounded-lg border border-slate-300 text-slate-700 text-sm font-medium hover:bg-slate-100"
          >
            Go to Chat
          </Link>
        </div>
      </div>
    </main>
  );
}

