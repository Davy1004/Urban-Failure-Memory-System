import { Waves } from "lucide-react";
import { useState, type FormEvent } from "react";

import { Button, Card, CardBody, Callout, Input, Label } from "@/components/ui";
import { useAuth } from "@/lib/auth";

export function LoginScreen() {
  const { signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signIn(email, password);
    } catch (err) {
      // The API returns one message for both a wrong email and a wrong
      // password; passing it through keeps that property intact.
      setError(err instanceof Error ? err.message : "Sign-in failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-full items-center justify-center px-5 py-16">
      <div className="w-full max-w-sm">
        <div className="mb-5 flex items-center gap-2">
          <Waves size={20} aria-hidden style={{ color: "var(--series-1)" }} />
          <span className="text-[16px] font-semibold tracking-tight">
            Urban Failure Memory System
          </span>
        </div>

        <Card>
          <CardBody className="pt-5">
            <form onSubmit={onSubmit} className="space-y-3.5">
              <div>
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="username"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="mt-1"
                />
              </div>

              {error ? (
                <Callout tone="critical" title="Sign-in failed">
                  {error}
                </Callout>
              ) : null}

              <Button
                type="submit"
                variant="primary"
                disabled={busy}
                className="w-full"
              >
                {busy ? "Signing in…" : "Sign in"}
              </Button>
            </form>
          </CardBody>
        </Card>

        <p className="mt-4 text-[12px] leading-relaxed text-[var(--text-muted)]">
          Officers do not self-register; an admin creates accounts. The session
          is held in memory only, so closing the tab signs you out.
        </p>
      </div>
    </div>
  );
}
