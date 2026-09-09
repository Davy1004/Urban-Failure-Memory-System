/**
 * The token-storage rule, pinned.
 *
 * The rule is not "persist the token" — it is that a bearer credential must not
 * survive a tab close on a shared municipal machine. `sessionStorage` satisfies
 * that and `localStorage` does not, and the difference is invisible in every
 * manual test anyone will run, because both look identical until someone else
 * sits down at the machine tomorrow. So it is asserted here.
 */
import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, me: vi.fn(), login: vi.fn() };
});

const api = await import("@/lib/api");
const { AuthProvider, useAuth } = await import("@/lib/auth");

const USER: import("@/lib/api").CurrentUser = {
  user_id: 1,
  name: "Demo Officer",
  email: "demo.officer@ufms-demo.org",
  role: "officer",
  department: null,
  city_id: 1,
  is_active: true,
};

function Probe() {
  const { user, restoring } = useAuth();
  if (restoring) return <p>restoring</p>;
  return <p>{user ? `signed in as ${user.email}` : "signed out"}</p>;
}

beforeEach(() => {
  sessionStorage.clear();
  localStorage.clear();
  api.setToken(null);
  vi.mocked(api.me).mockReset();
});

describe("token storage", () => {
  it("writes the token to sessionStorage and never to localStorage", () => {
    api.setToken("a-token");
    expect(sessionStorage.getItem("ufms.access_token")).toBe("a-token");
    expect(localStorage.length).toBe(0);
  });

  it("clears the stored token on sign-out", () => {
    api.setToken("a-token");
    api.setToken(null);
    expect(sessionStorage.getItem("ufms.access_token")).toBeNull();
    expect(api.getToken()).toBeNull();
  });

  it("sends the stored token as a bearer header", async () => {
    api.setToken("a-token");
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(USER), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const { me } = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
    await me();
    const headers = (fetchMock.mock.calls[0][1] as RequestInit).headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer a-token");
    vi.unstubAllGlobals();
  });
});

describe("session restore", () => {
  it("signs the user back in from a stored token, without a login screen", async () => {
    api.setToken("a-token");
    vi.mocked(api.me).mockResolvedValue(USER);

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    // Crucially not "signed out" first: a flash of the login form on every
    // refresh is the bug this restore exists to prevent.
    expect(screen.getByText("restoring")).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByText(/signed in as demo\.officer/)).toBeInTheDocument(),
    );
  });

  it("discards a token the server rejects, rather than leaving it in storage", async () => {
    api.setToken("an-expired-token");
    vi.mocked(api.me).mockRejectedValue(new api.ApiError(401, "Not authenticated"));

    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );

    await waitFor(() => expect(screen.getByText("signed out")).toBeInTheDocument());
    expect(sessionStorage.getItem("ufms.access_token")).toBeNull();
  });

  it("goes straight to signed out when there is no stored token", async () => {
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    expect(screen.getByText("signed out")).toBeInTheDocument();
    expect(api.me).not.toHaveBeenCalled();
  });
});
