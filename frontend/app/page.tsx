"use client";

import { useAuth, SignInButton, UserButton } from "@clerk/nextjs";
import { useRouter } from "next/navigation";

export default function Home() {
  const { isSignedIn } = useAuth();
  const router = useRouter();

  return (
    <div style={{
      minHeight: "100vh",
      background: "#050810",
      fontFamily: "monospace",
      color: "#e0f0ff",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      padding: "40px 20px",
      position: "relative",
    }}>
      {isSignedIn && (
        <div style={{ position: "absolute", top: 24, right: 24 }}>
          <UserButton afterSignOutUrl="/" />
        </div>
      )}

      <div style={{ textAlign: "center", marginBottom: 48 }}>
        <h1 style={{
          fontSize: "clamp(32px, 6vw, 64px)",
          fontWeight: "bold",
          color: "#00e5ff",
          letterSpacing: "0.15em",
          margin: 0,
          textShadow: "0 0 30px rgba(0,229,255,0.4)",
        }}>
          NEXUS ORACLE
        </h1>
        <p style={{ fontSize: 14, color: "rgba(0,229,255,0.5)", letterSpacing: "0.3em", marginTop: 8 }}>
          v4.0 // PRODUCTION // SATSON
        </p>
      </div>

      <div style={{ maxWidth: 560, textAlign: "center", marginBottom: 48, borderLeft: "2px solid rgba(0,229,255,0.3)", paddingLeft: 24 }}>
        <p style={{ fontSize: 16, lineHeight: 1.8, color: "rgba(224,240,255,0.8)", margin: 0 }}>
          14-node sovereign AI research engine.<br />
          Not a chatbot. Ask it hard questions.
        </p>
        <p style={{ fontSize: 13, color: "rgba(224,240,255,0.4)", marginTop: 12 }}>
          Generate - Critique - Repair - Verify
        </p>
      </div>

      <div style={{ display: "flex", gap: 16, marginBottom: 48, flexWrap: "wrap", justifyContent: "center" }}>
        {[
          { mode: "QUICK", desc: "Instant answers", color: "#00e676" },
          { mode: "CODE", desc: "Executable code", color: "#ffb300" },
          { mode: "SOVEREIGN", desc: "Deep research pipeline", color: "#00e5ff" },
        ].map(({ mode, desc, color }) => (
          <div key={mode} style={{ border: `1px solid ${color}33`, padding: "12px 20px", background: `${color}08`, minWidth: 140, textAlign: "center" }}>
            <div style={{ color, fontSize: 13, fontWeight: "bold", letterSpacing: "0.2em" }}>{mode}</div>
            <div style={{ color: "rgba(224,240,255,0.5)", fontSize: 11, marginTop: 4 }}>{desc}</div>
          </div>
        ))}
      </div>

      {isSignedIn ? (
        <button onClick={() => router.push("/war-room")} style={{ background: "rgba(0,229,255,0.1)", border: "1px solid #00e5ff", color: "#00e5ff", padding: "14px 48px", fontSize: 13, letterSpacing: "0.3em", cursor: "pointer", fontFamily: "monospace" }}>
          ENTER WAR ROOM
        </button>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
          <SignInButton mode="modal" fallbackRedirectUrl="/war-room">
            <button style={{ background: "transparent", border: "1px solid #00e5ff", color: "#00e5ff", padding: "14px 48px", fontSize: 13, letterSpacing: "0.3em", cursor: "pointer", fontFamily: "monospace" }}>
              ACCESS THE WAR ROOM
            </button>
          </SignInButton>
          <p style={{ fontSize: 11, color: "rgba(224,240,255,0.3)", letterSpacing: "0.1em", margin: 0 }}>
            Free access during beta
          </p>
        </div>
      )}

      <div style={{ position: "absolute", bottom: 24, fontSize: 11, color: "rgba(224,240,255,0.2)", letterSpacing: "0.1em" }}>
        SATSON // NEXUS GENESIS // PHASE 2
      </div>
    </div>
  );
}
