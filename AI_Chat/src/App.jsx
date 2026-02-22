import { useState, useEffect } from "react";
import { healthCheck } from "./api/client";
import Sidebar from "./components/Sidebar";
import ChatPanel from "./components/ChatPanel";
import MemoryPanel from "./components/MemoryPanel";
import SearchPanel from "./components/SearchPanel";
import "./App.css";

export default function App() {
  const [activeView, setActiveView] = useState("chat");
  const [online, setOnline] = useState(false);

  useEffect(() => {
    const check = async () => {
      try {
        await healthCheck();
        setOnline(true);
      } catch {
        setOnline(false);
      }
    };
    check();
    const interval = setInterval(check, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app">
      <Sidebar
        activeView={activeView}
        onChangeView={setActiveView}
        online={online}
      />
      <main className="main-content">
        {activeView === "chat" && <ChatPanel />}
        {activeView === "memory" && <MemoryPanel />}
        {activeView === "search" && <SearchPanel />}
      </main>
    </div>
  );
}
