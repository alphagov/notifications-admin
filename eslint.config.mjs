import globals from "globals";
import jestConfig from 'eslint-plugin-jest';
import js from "@eslint/js";

export default [
  {
    files: [
      "app/assets/**/*.{js,mjs}",
      "tests/**/*.{js,mjs}"
    ],
    rules: {
      ...js.configs.recommended.rules,
      "semi": ["error", "always"],
      "no-prototype-builtins": "warn",
      "no-unused-vars": "warn",
      "no-extra-boolean-cast": "warn",
      "no-undef": "warn",
      "no-useless-escape": "warn",
      "no-unexpected-multiline": "warn",
      //needs more standardjs rules
    },
    ignores: [
      'tests/**/*.{js,mjs}'
    ],
  },
  {
    files: ["app/assets/**/*.js"],
    languageOptions: {
      sourceType: "commonjs",
      globals: {
        ...globals.browser,
        '$': 'writable',
        "GOVUK": "readonly"
      }
    },
  },
  {
    files: ["**/*.mjs"],
    languageOptions: {
      sourceType: "module",
      globals: {
        ...globals.browser
      }
    }
  },
  {
    files: ['**/*.test.{js,mjs}'],
    ...jestConfig.configs['flat/recommended'],
    rules: {
      "jest/no-disabled-tests": "error",
      "jest/no-focused-tests": "warn",
    }
  },
];