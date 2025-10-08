import { nodeResolve } from '@rollup/plugin-node-resolve';
import multi from '@rollup/plugin-multi-entry';
import terser from '@rollup/plugin-terser';
import copy from 'rollup-plugin-copy';
import styles from "rollup-plugin-styler";
import postCSSReplace from 'postcss-replace';

// toggle to enable rebrand styles
const enableRebrand = true;
const paths = {
  src: 'app/assets/',
  dist: 'app/static/',
  npm: 'node_modules/',
  govuk_frontend: 'node_modules/govuk-frontend/dist/'
};

// separate path config for govuk-frontend assets, so we can manage rebrand paths easily
const govukFrontendAssetPaths = {
  images: `${paths.govuk_frontend}govuk/assets/${enableRebrand ? 'rebrand/': ''}images/**/*`,
  fonts: `${paths.govuk_frontend}govuk/assets/fonts/**/*`,
  manifest: `${paths.govuk_frontend}govuk/assets/${enableRebrand ? 'rebrand/': ''}manifest.json`,
};

const isDevelopment = Boolean(process.env.NOTIFY_ENVIRONMENT === 'development')

export default [
  // ESM compilation and copy static assets
  {
    input: paths.src + 'javascripts/esm/all-esm.mjs',
    output: {
      dir: paths.dist + 'javascripts/',
      entryFileNames: 'all-esm.mjs',
      format: 'es',
      sourcemap: true
    },
    plugins: [
      nodeResolve(),
      terser(),
      // copy images, error pages and govuk-frontend static assets
      copy({
        targets: [
          { src: paths.src + 'error_pages/**/*', dest: paths.dist + 'error_pages/' },
          { src: paths.src + 'images/**/*', dest: paths.dist + 'images/' },
          { src: govukFrontendAssetPaths.images, dest: paths.dist + 'images/' },
          { src: govukFrontendAssetPaths.fonts, dest: paths.dist + 'fonts/' },
          { src: govukFrontendAssetPaths.manifest, dest: paths.dist }
        ]
      }),
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
            "mixed-decls",
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
  },
  // ES5 JS compilation
  {
    input: [
      paths.npm + 'jquery/dist/jquery.min.js',
      paths.npm + 'timeago/jquery.timeago.js',
      paths.npm + 'textarea-caret/index.js',
      paths.npm + 'cbor-js/cbor.js',
      paths.src + 'javascripts/modules.js',
      paths.src + 'javascripts/govuk-frontend-toolkit/show-hide-content.js',
      paths.src + 'javascripts/stick-to-window-when-scrolling.js',
      paths.src + 'javascripts/cookieCleanup.js',
      paths.src + 'javascripts/radioSelect.js',
      paths.src + 'javascripts/updateContent.js',
      paths.src + 'javascripts/preventDuplicateFormSubmissions.js',
      paths.src + 'javascripts/fullscreenTable.js',
      paths.src + 'javascripts/templateFolderForm.js',
      paths.src + 'javascripts/registerSecurityKey.js',
      paths.src + 'javascripts/authenticateSecurityKey.js',
      paths.src + 'javascripts/updateStatus.js',
      paths.src + 'javascripts/errorBanner.js',
      paths.src + 'javascripts/removeInPresenceOf.js',
      paths.src + 'javascripts/main.js',
    ],
    output: {
      dir: paths.dist + 'javascripts/',
      sourcemap: true
    },
    moduleContext: {
      './node_modules/jquery/dist/jquery.min.js': 'window',
      './node_modules/cbor-js/cbor.js': 'window',
    },
    plugins: [
      nodeResolve(),
      multi({
        entryFileName: 'all.js'
      }),
      terser({
        ecma: '5'
      }),
    ]
  }
];
