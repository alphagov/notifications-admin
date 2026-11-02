import { nodeResolve } from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import terser from '@rollup/plugin-terser';
import { copy } from '@web/rollup-plugin-copy';
import styles from "rollup-plugin-styler";
import postCSSReplace from 'postcss-replace';

const paths = {
  src: 'app/assets/',
  dist: 'app/static/',
  npm: 'node_modules/',
  govuk_frontend: 'node_modules/govuk-frontend/dist/'
};

const isDevelopment = Boolean(process.env.NOTIFY_ENVIRONMENT === 'development')

export default [
  // ESM compilation and copy static assets
  {
    input: paths.src + 'javascripts/esm/all-esm.mjs',
    output: {
      dir: paths.dist,
      entryFileNames: 'javascripts/all-esm.mjs',
      format: 'es',
      sourcemap: true
    },
    plugins: [
      commonjs(),
      nodeResolve(),
      terser(),
      // copy images and error pages
      copy({
        rootDir: paths.src,
        patterns: ['error_pages/**/*', 'images/**/*']
      }),
      // govuk-frontend static assets
      copy({
        rootDir: `${paths.govuk_frontend}govuk/assets/`,
        patterns: ['images/**/*', 'fonts/**/*', 'manifest.json']
      })
    ]
  },
  // SCSS compilation
  {
    input: [
      paths.src + 'stylesheets/main.scss',
      paths.src + 'stylesheets/print.scss'
    ],
    output: {
      dir: paths.dist + 'stylesheets/',
      assetFileNames: "[name][extname]",
    },
    plugins: [
      // https://anidetrix.github.io/rollup-plugin-styles/interfaces/types.Options.html
      styles({
        mode: "extract",
        sass: {
          includePaths: [
            paths.govuk_frontend,
            paths.npm
          ],
          silenceDeprecations: [
            "global-builtin",
            "color-functions",
            "slash-div",
            "import"
          ]
        },
        minimize: true,
        url: false,
        sourceMap: true,
        plugins:[
          // Rewrite /static prefix for URLs in CSS files for production
          !isDevelopment && postCSSReplace({
            pattern: /\/static\//g,
            data: {
              replaceAll: '/'
            }
          }),
        ]
      }),
    ]
  }
];
