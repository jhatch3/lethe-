"use client";

import { motion } from "framer-motion";
import { useEffect, useState } from "react";

export default function Home() {
  const [message, setMessage] = useState<string>("…");

  useEffect(() => {
    const url = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    fetch(url)
      .then((r) => r.json())
      .then((d) => setMessage(d.message ?? "no message"))
      .catch(() => setMessage("backend offline"));
  }, []);

  return (
    <main className="flex flex-1 items-center justify-center px-6">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, ease: "easeOut" }}
        className="flex flex-col items-center gap-4 text-center"
      >
        <h1 className="text-5xl font-semibold tracking-tight">Lethe</h1>
        <p className="text-zinc-500 dark:text-zinc-400">
          Medical bills, audited by AI consensus.
        </p>
        <motion.code
          key={message}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.4 }}
          className="mt-6 rounded-md bg-zinc-100 px-3 py-1.5 text-sm dark:bg-zinc-900"
        >
          coordinator: {message}
        </motion.code>
      </motion.div>
    </main>
  );
}
