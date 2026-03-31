/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/accounts/**/*.html",
    "./templates/pages/**/*.html",
    "./templates/pages/includes/**/*.html"
  ],
  theme: {
    extend: {
      colors: {
        primary: "rgb(255, 60, 0)",
        "primary-dark": "rgb(217, 38, 0)",
        "primary-darker": "rgb(175, 20, 0)",
        "primary-darkest": "rgb(67, 26, 0)"
      },
      fontFamily: {
        outfit: ["Outfit", "sans-serif"]
      }
    }
  },
  plugins: []
};
