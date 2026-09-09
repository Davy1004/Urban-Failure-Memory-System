import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "@/components/AppShell";
import { Loading } from "@/components/ui";
import { useAuth } from "@/lib/auth";
import { LoginScreen } from "@/screens/LoginScreen";
import { WatchlistScreen } from "@/screens/WatchlistScreen";

// The watchlist is the landing screen and is plain DOM, so it ships in the
// entry chunk. The other three pull in Recharts and Leaflet — roughly 600 kB
// between them — and there is no reason to make an officer download a map
// before they have asked for one.
const IndexScreen = lazy(() =>
  import("@/screens/IndexScreen").then((m) => ({ default: m.IndexScreen })),
);
const EmergingScreen = lazy(() =>
  import("@/screens/EmergingScreen").then((m) => ({ default: m.EmergingScreen })),
);
const AllocationScreen = lazy(() =>
  import("@/screens/AllocationScreen").then((m) => ({ default: m.AllocationScreen })),
);

export function App() {
  const { user, restoring } = useAuth();

  // A token from sessionStorage is being exchanged for a user. Showing the login
  // screen here would flash a sign-in form at an officer who is already signed
  // in, every time they refresh or follow a deep link.
  if (restoring) return <Loading label="Restoring your session" />;

  // No token, no screens. There is nothing public here: every figure is a
  // measurement about a specific city's infrastructure.
  if (!user) return <LoginScreen />;

  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Navigate to="/watchlist" replace />} />
        <Route path="/watchlist" element={<WatchlistScreen />} />
        <Route
          path="/index"
          element={
            <Suspense fallback={<Loading label="Loading the ward index" />}>
              <IndexScreen />
            </Suspense>
          }
        />
        <Route
          path="/emerging"
          element={
            <Suspense fallback={<Loading label="Loading the emerging watch" />}>
              <EmergingScreen />
            </Suspense>
          }
        />
        <Route
          path="/allocation"
          element={
            <Suspense fallback={<Loading label="Loading allocation" />}>
              <AllocationScreen />
            </Suspense>
          }
        />
        <Route path="*" element={<Navigate to="/watchlist" replace />} />
      </Route>
    </Routes>
  );
}
