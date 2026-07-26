"use strict";

const js = require("@eslint/js");
const globals = require("globals");

module.exports = [
  {
    ignores: ["node_modules/**", "public/images/**"],
  },

  // Backend: CommonJS running on Node
  {
    files: ["index.js", "eslint.config.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "commonjs",
      globals: globals.node,
    },
    ...js.configs.recommended,
    rules: {
      ...js.configs.recommended.rules,
      "no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
    },
  },

  // Frontend: plain browser scripts, no modules, no bundler.
  // script.js and microphone-fix.js share one global scope via <script> tags,
  // so cross-file references are expected rather than errors.
  {
    files: ["public/js/**/*.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "script",
      globals: {
        ...globals.browser,
        // Provided by <script src="/socket.io/socket.io.js"> in index.html.
        // Symbols shared between script.js and microphone-fix.js are NOT listed
        // here - declaring them would turn their real declarations into
        // no-redeclare errors. Cross-file uses surface as no-undef warnings.
        io: "readonly",
      },
    },
    ...js.configs.recommended,
    rules: {
      ...js.configs.recommended.rules,
      "no-unused-vars": ["warn", { argsIgnorePattern: "^_" }],
      // Functions are declared across files and called before definition order.
      "no-undef": "warn",
    },
  },
];
