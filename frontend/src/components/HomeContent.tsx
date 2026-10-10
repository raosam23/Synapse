"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useAuthStore } from "@/store/authStore";

const HomeContent = () => {
  const { user, isLoading, checkAuth, logout } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error: unknown) {
      console.error("Logout failed:", error);
    }
  };

  if (isLoading) return <div>Loading...</div>;

  return (
    <>
      {user ? (
        <div>
          <p>Welcome, {user.name || user.email}!</p>
          <button onClick={handleLogout}>Logout</button>
        </div>
      ) : (
        <div>
          <p>Please log in or register to continue</p>
          <Link href="/login">Login</Link> |{" "}
          <Link href="/register">Register</Link>
        </div>
      )}
    </>
  );
};

export default HomeContent;
