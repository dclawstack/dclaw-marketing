import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8 text-center">
      <h1 className="mb-4 text-4xl font-bold text-foreground">DClaw Marketing</h1>
      <p className="mb-8 text-lg text-muted-foreground">Market smarter with AI</p>
      <Link
        href="/login"
        className="rounded-md bg-primary px-6 py-3 font-medium text-primary-foreground transition-colors hover:bg-primary/90"
      >
        Sign in
      </Link>
    </main>
  );
}
