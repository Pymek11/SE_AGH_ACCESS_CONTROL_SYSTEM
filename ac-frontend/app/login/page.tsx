import React from "react";

export default function LoginPage() {
  return (
    <div className="min-h-[70vh] flex items-start justify-center py-16 px-4">
      <form className="w-full max-w-md bg-[#1f1f1f] border border-gray-800 rounded-lg p-6 shadow-lg">
        <h1 className="text-2xl font-semibold text-white mb-4">Sign in</h1>

        <label className="block mb-3">
          <span className="text-sm text-gray-300">Email</span>
          <input
            type="email"
            name="email"
            className="mt-1 w-full rounded bg-[#0f0f0f] border border-gray-700 px-3 py-2 text-white"
            placeholder="you@example.com"
          />
        </label>

        <label className="block mb-3">
          <span className="text-sm text-gray-300">Password</span>
          <input
            type="password"
            name="password"
            className="mt-1 w-full rounded bg-[#0f0f0f] border border-gray-700 px-3 py-2 text-white"
            placeholder="••••••••"
          />
        </label>

        <div className="flex items-center justify-between mb-4">
          <label className="inline-flex items-center text-sm text-gray-300">
            <input type="checkbox" name="remember" className="mr-2" />
            Remember me
          </label>
          <a href="#" className="text-sm text-indigo-400 hover:underline">
            Forgot?
          </a>
        </div>

        <button
          type="submit"
          className="w-full py-2 rounded bg-purple-900 hover:bg-purple-800 text-white font-medium"
        >
          Sign in
        </button>

        <p className="mt-4 text-sm text-gray-400">
          Don't have an account?{" "}
          <a href="#" className="text-indigo-400 hover:underline">
            Sign up
          </a>
        </p>
      </form>
    </div>
  );
}