import js from '@eslint/js';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import tseslint from 'typescript-eslint';
import prettier from 'eslint-config-prettier';

export default tseslint.config(
  { ignores: ['dist'] },
  {
    files: ['**/*.{ts,tsx}'],
    extends: [js.configs.recommended, tseslint.configs.recommended, reactRefresh.configs.vite],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
    },
    rules: {
      // eslint-plugin-react-hooks v7's recommended preset also enables the new
      // React Compiler rules (set-state-in-effect, immutability, purity, …),
      // which flag idiomatic, working code (e.g. fetch-on-mount effects). We
      // scope to the long-standing correctness rules so linting stays
      // behavior-neutral; adopting the compiler rules is a separate effort.
      'react-hooks/rules-of-hooks': 'error',
      'react-hooks/exhaustive-deps': 'warn',
    },
  },
  // Keep last: turns off ESLint rules that would conflict with Prettier.
  prettier,
);
