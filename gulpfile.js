// GULPFILE
// - - - - - - - - - - - - - - -
// This file processes all of the assets in the "src" folder
// and outputs the finished files in the "dist" folder.

// 1. LIBRARIES
// - - - - - - - - - - - - - - -
const { src, pipe, dest, series, parallel, watch } = require('gulp');
const rollupPluginNodeResolve = require('rollup-plugin-node-resolve');
const streamqueue = require('streamqueue');
const stylish = require('jshint-stylish');
const del = require('del');

const plugins = {};
plugins.addSrc = require('gulp-add-src');
plugins.babel = require('gulp-babel');
plugins.cleanCSS = require('gulp-clean-css');
plugins.concat = require('gulp-concat');
plugins.cssUrlAdjuster = require('gulp-css-url-adjuster');
plugins.jshint = require('gulp-jshint');
plugins.prettyerror = require('gulp-prettyerror');
plugins.rollup = require('gulp-better-rollup')
plugins.sass = require('gulp-sass')(require('sass'));
plugins.sassLint = require('gulp-sass-lint');
plugins.uglify = require('gulp-uglify');

// 2. CONFIGURATION
// - - - - - - - - - - - - - - -
const paths = {
  src: 'app/assets/',
  dist: 'app/static/',
  npm: 'node_modules/',
  govuk_frontend: 'node_modules/govuk-frontend/dist/'
};
// Rewrite /static prefix for URLs in CSS files
let staticPathMatcher = new RegExp('^\/static\/');
if (process.env.NOTIFY_ENVIRONMENT == 'development') { // pass through if on development
  staticPathMatcher = url => url;
}

// 3. TASKS
// - - - - - - - - - - - - - - -

// Move GOV.UK template resources

const copy = {
  error_pages: () => {
    return src(paths.src + 'error_pages/**/*')
      .pipe(dest(paths.dist + 'error_pages/'))
  },
  govuk_frontend: {
    fonts: () => {
      return src(paths.govuk_frontend + 'govuk/assets/fonts/**/*')
        .pipe(dest(paths.dist + 'fonts/'));
    },
    header_icon_manifest: () => {
      return src(paths.govuk_frontend + 'govuk/assets/manifest.json')
        .pipe(dest(paths.dist));
    },
  }
};




const javascripts = () => {
  // JS from third-party sources
  // We assume none of it will need to pass through Babel
  const vendored = src(paths.src + 'javascripts/esm/all.mjs')
    // Use Rollup to combine all JS in ECMAScript module format into a Immediately Invoked Function
    // Expression (IIFE) to:
    // - deliver it in one bundle
    // - allow it to run in browsers without support for JS Modules
    .pipe(plugins.rollup(
      {
        plugins: [
          // determine module entry points from either 'module' or 'main' fields in package.json
          rollupPluginNodeResolve({
            mainFields: ['module', 'main']
          })
        ]
      },
      {
        format: 'iife',
        name: 'GOVUK'
      }
    ))
    // return a stream which pipes these files before the ECMAScript modules bundle
    .pipe(plugins.addSrc.prepend([
      paths.npm + 'hogan.js/dist/hogan-3.0.2.js',
      paths.npm + 'jquery/dist/jquery.min.js',
      paths.npm + 'query-command-supported/dist/queryCommandSupported.min.js',
      paths.npm + 'timeago/jquery.timeago.js',
      paths.npm + 'textarea-caret/index.js',
      paths.npm + 'cbor-js/cbor.js'
    ]));

  // JS local to this application
  const local = src([
    paths.src + 'javascripts/modules.js',
    paths.src + 'javascripts/govuk-frontend-toolkit/show-hide-content.js',
    paths.src + 'javascripts/stick-to-window-when-scrolling.js',
    paths.src + 'javascripts/cookieCleanup.js',
    paths.src + 'javascripts/copyToClipboard.js',
    paths.src + 'javascripts/autofocus.js',
    paths.src + 'javascripts/enhancedTextbox.js',
    paths.src + 'javascripts/fileUpload.js',
    paths.src + 'javascripts/radioSelect.js',
    paths.src + 'javascripts/updateContent.js',
    paths.src + 'javascripts/listEntry.js',
    paths.src + 'javascripts/liveSearch.js',
    paths.src + 'javascripts/preventDuplicateFormSubmissions.js',
    paths.src + 'javascripts/fullscreenTable.js',
    paths.src + 'javascripts/radios-with-images.js',
    paths.src + 'javascripts/previewPane.js',
    paths.src + 'javascripts/colourPreview.js',
    paths.src + 'javascripts/liveCheckboxControls.js',
    paths.src + 'javascripts/templateFolderForm.js',
    paths.src + 'javascripts/addBrandingOptionsForm.js',
    paths.src + 'javascripts/setAuthTypeForm.js',
    paths.src + 'javascripts/collapsibleCheckboxes.js',
    paths.src + 'javascripts/registerSecurityKey.js',
    paths.src + 'javascripts/authenticateSecurityKey.js',
    paths.src + 'javascripts/updateStatus.js',
    paths.src + 'javascripts/errorBanner.js',
    paths.src + 'javascripts/homepage.js',
    paths.src + 'javascripts/removeInPresenceOf.js',
    paths.src + 'javascripts/main.js',
  ])
  .pipe(plugins.prettyerror())
  .pipe(plugins.babel({
    presets: ['@babel/preset-env']
  }));

  // return single stream of all vinyl objects piped from the end of the vendored stream, then
  // those from the end of the local stream
  return streamqueue({ objectMode: true }, vendored, local)
    .pipe(plugins.uglify())
    .pipe(plugins.concat('all.js'))
    .pipe(dest(paths.dist + 'javascripts/'))
};


const sass = () => {
  return src(paths.src + '/stylesheets/*.scss')
    .pipe(plugins.prettyerror())
    .pipe(plugins.sass.sync({
      includePaths: [
        paths.govuk_frontend,
        paths.npm
      ]
    }))
    .pipe(plugins.cssUrlAdjuster({
      replace: [staticPathMatcher, '/']
    }))
    // cssUrlAdjuster outputs uncompressed CSS so we need to perform the compression here
    .pipe(plugins.cleanCSS({ compatibility: '*' }))
    .pipe(dest(paths.dist + 'stylesheets/'))
};


// Copy images

const images = () => {
  return src([
      paths.src + 'images/**/*',
      paths.govuk_frontend + 'govuk/assets/images/**/*'
    ])
    .pipe(dest(paths.dist + 'images/'))
};


const watchFiles = {
  javascripts: (cb) => {
    watch([paths.src + 'javascripts/**/*'], series(clean.javascripts, javascripts));
    cb();
  },
  sass: (cb) => {
    watch([paths.src + 'stylesheets/**/*'], series(clean.sass, sass));
    cb();
  },
  images: (cb) => {
    watch([paths.src + 'images/**/*'], series(clean.images, images));
    cb();
  },
  self: (cb) => {
    watch(['gulpfile.js'], defaultTask);
    cb();
  }
};


const lint = {
  'sass': () => {
    return src([
        paths.src + 'stylesheets/*.scss',
        paths.src + 'stylesheets/components/*.scss',
        paths.src + 'stylesheets/views/*.scss',
      ])
      .pipe(plugins.sassLint({
        'options': { 'formatter': 'stylish' },
        'rules': { 'mixins-before-declarations': [2, { 'exclude': ['media', 'govuk-media-query'] } ] }
      }))
      .pipe(plugins.sassLint.format())
      .pipe(plugins.sassLint.failOnError());
  },
  'js': (cb) => {
    return src(
        paths.src + 'javascripts/**/*.js'
      )
      .pipe(plugins.jshint())
      .pipe(plugins.jshint.reporter(stylish))
      .pipe(plugins.jshint.reporter('fail'))
  }
};

const clean = {
  everything: async function cleanEverything(cb) {
    await del([`${paths.dist}/*`]);
    cb();
  },
  javascripts: async function cleanJavascripts(cb) {
    await del([`${paths.dist}/javascripts/*`]);
    cb();
  },
  sass: async function cleanSass(cb) {
    await del([`${paths.dist}/stylesheets/*`]);
    cb();
  },
  images: async function cleanImages(cb) {
    await del([`${paths.dist}/images/*`]);
    cb();
  }
}

// Default: compile everything
const defaultTask = series(
  clean.everything,
  parallel(
    copy.govuk_frontend.fonts,
    copy.govuk_frontend.header_icon_manifest,
    copy.error_pages,
    images,
    javascripts,
    sass
  )
);


// Watch for changes and re-run tasks
const watchForChanges = parallel(
  watchFiles.javascripts,
  watchFiles.sass,
  watchFiles.images,
  watchFiles.self
);


exports.default = defaultTask;

exports.lint = parallel(lint.sass, lint.js);

// Optional: recompile on changes
exports.watch = series(defaultTask, watchForChanges);
