import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        mono: ["DM Mono", "monospace"],
      },
      colors: {
        teal: {
          400: "#2dd4bf",
          500: "#14b8a6",
        },
      },
    },
  },
  plugins: [],
};
export default config;
