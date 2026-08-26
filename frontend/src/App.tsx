import { useEffect } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { AboutPage } from "./pages/AboutPage";
import { BatchPage } from "./pages/BatchPage";
import { ChannelPage } from "./pages/ChannelPage";
import { CookiePage } from "./pages/CookiePage";
import { DownloadsPage } from "./pages/DownloadsPage";
import { ProxyPage } from "./pages/ProxyPage";
import { SinglePage } from "./pages/SinglePage";
import { VersionsPage } from "./pages/VersionsPage";
import { useAppStore } from "./stores/appStore";

export default function App() {
  const bootstrap = useAppStore((state) => state.bootstrap);
  useEffect(() => { void bootstrap(); }, [bootstrap]);
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<SinglePage />} />
          <Route path="batch" element={<BatchPage />} />
          <Route path="channel" element={<ChannelPage />} />
          <Route path="downloads" element={<DownloadsPage />} />
          <Route path="cookies" element={<CookiePage />} />
          <Route path="proxy" element={<ProxyPage />} />
          <Route path="versions" element={<VersionsPage />} />
          <Route path="about" element={<AboutPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

