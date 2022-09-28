// GULPFILE
// - - - - - - - - - - - - - - -
// This file processes all of the assets in the "src" folder
// and outputs the finished files in the "dist" folder.

// 1. LIBRARIES
// - - - - - - - - - - - - - - -
const { src, pipe, dest, series, parallel, watch } = require('gulp');
const rollupPluginCommonjs = require('rollup-plugin-commonjs');
const rollupPluginNodeResolve = require('rollup-plugin-node-resolve');
const streamqueue = require('streamqueue');
const stylish = require('jshint-stylish');

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
  templates: 'app/templates/',
  npm: 'node_modules/',
  toolkit: 'node_modules/govuk_frontend_toolkit/',
  govuk_frontend: 'node_modules/govuk-frontend/'
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
      return src(paths.govuk_frontend + 'assets/fonts/**/*')
        .pipe(dest(paths.dist + 'fonts/'));
    },
    templates: (cb) => {
      // Put names of GOVUK Frontend templates here
      const _templates = [
        'template',
        'skip-link',
        'header',
        'footer',
        'back-link',
        'details',
        'button',
        'error-message',
        'fieldset',
        'hint',
        'label',
        'checkboxes',
        'radios',
        'input',
        'inset-text',
        'textarea'
      ];
      let done = 0;

      // Copy the templates for each component across, preserving their folder structure
      _templates.forEach(name => {
        let _src = [
          paths.govuk_frontend + 'components/' + name + '/macro.njk',
          paths.govuk_frontend + 'components/' + name + '/template.njk'
        ];
        let _dest = paths.templates + 'vendor/govuk-frontend/components/' + name;

        // template.njk isn't a component
        if (name === 'template') {
          _src = paths.govuk_frontend + 'template.njk';
          _dest = paths.templates + 'vendor/govuk-frontend';
        }

        src(_src)
        .pipe(
          dest(_dest)
          .on('end', () => { // resolve promise if all copied
            done = done + 1;
            if (done === _templates.length) {
              cb();
            }
          })
        )
      });
    }
  },
  leaflet: {
    js: () => {
      return src(paths.npm + 'leaflet/dist/leaflet.js')
        .pipe(dest(paths.dist + 'javascripts/'))
    }
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
          }),
          // gulp rollup runs on nodeJS so reads modules in commonJS format
          // this adds node_modules to the require path so it can find the GOVUK Frontend modules
          rollupPluginCommonjs({
            include: 'node_modules/**'
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
    paths.src + 'javascripts/previewPane.js',
    paths.src + 'javascripts/colourPreview.js',
    paths.src + 'javascripts/templateFolderForm.js',
    paths.src + 'javascripts/addEmailBrandingOptionsForm.js',
    paths.src + 'javascripts/collapsibleCheckboxes.js',
    paths.src + 'javascripts/radioSlider.js',
    paths.src + 'javascripts/registerSecurityKey.js',
    paths.src + 'javascripts/authenticateSecurityKey.js',
    paths.src + 'javascripts/updateStatus.js',
    paths.src + 'javascripts/errorBanner.js',
    paths.src + 'javascripts/homepage.js',
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
  return src([
      paths.src + '/stylesheets/main*.scss',
      paths.src + '/stylesheets/map.scss',
      paths.src + '/stylesheets/print.scss'
    ])
    .pipe(plugins.prettyerror())
    .pipe(plugins.sass.sync({
      includePaths: [
        paths.npm + 'govuk-elements-sass/public/sass/',
        paths.toolkit + 'stylesheets/',
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
      paths.toolkit + 'images/**/*',
      paths.template + 'assets/images/**/*',
      paths.govuk_frontend + 'assets/images/**/*'
    ])
    .pipe(dest(paths.dist + 'images/'))
};


const watchFiles = {
  javascripts: (cb) => {
    watch([paths.src + 'javascripts/**/*'], javascripts);
    cb();
  },
  sass: (cb) => {
    watch([paths.src + 'stylesheets/**/*'], sass);
    cb();
  },
  images: (cb) => {
    watch([paths.src + 'images/**/*'], images);
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


// Default: compile everything
const defaultTask = parallel(
  parallel(
    copy.govuk_frontend.fonts,
    copy.govuk_frontend.templates,
    images,
    copy.leaflet.js
  ),
  series(
    copy.error_pages,
    series(
      javascripts
    ),
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

exports.lint = series(lint.sass, lint.js);

// Optional: recompile on changes
exports.watch = series(defaultTask, watchForChanges);
