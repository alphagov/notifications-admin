// GULPFILE
// - - - - - - - - - - - - - - -
// This file processes all of the assets in the "src" folder
// and outputs the finished files in the "dist" folder.

// 1. LIBRARIES
// - - - - - - - - - - - - - - -
const { src, pipe, dest, series, parallel, watch } = require('gulp');
const rollup = require('rollup');
const rollupPluginCommonjs = require('rollup-plugin-commonjs');
const rollupPluginNodeResolve = require('rollup-plugin-node-resolve');
const stylish = require('jshint-stylish');

const plugins = {};
plugins.addSrc = require('gulp-add-src');
plugins.babel = require('gulp-babel');
plugins.base64 = require('gulp-base64-inline');
plugins.concat = require('gulp-concat');
plugins.cssUrlAdjuster = require('gulp-css-url-adjuster');
plugins.jshint = require('gulp-jshint');
plugins.prettyerror = require('gulp-prettyerror');
plugins.sass = require('gulp-sass');
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
    }
  }
};


const bundleJavaScriptModules = async function () {
  const bundle = await rollup.rollup({
    input: paths.src + 'javascripts/modules/all.mjs',
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
  });

  // write resulting module to Immediately Invoked Function Expression (IIFE) format
  // map the exported code to the window.GOVUK namespace
  await bundle.write({
    file: paths.src + 'javascripts/modules/all.js',
    format: 'iife',
    name: 'GOVUK'
  });
};


const javascripts = () => {
  return src([
      paths.toolkit + 'javascripts/govuk/modules.js',
      paths.toolkit + 'javascripts/govuk/show-hide-content.js',
      paths.src + 'javascripts/govuk/cookie-functions.js',
      paths.src + 'javascripts/cookieMessage.js',
      paths.src + 'javascripts/stick-to-window-when-scrolling.js',
      paths.src + 'javascripts/detailsPolyfill.js',
      paths.src + 'javascripts/apiKey.js',
      paths.src + 'javascripts/autofocus.js',
      paths.src + 'javascripts/enhancedTextbox.js',
      paths.src + 'javascripts/fileUpload.js',
      paths.src + 'javascripts/radioSelect.js',
      paths.src + 'javascripts/updateContent.js',
      paths.src + 'javascripts/listEntry.js',
      paths.src + 'javascripts/liveSearch.js',
      paths.src + 'javascripts/errorTracking.js',
      paths.src + 'javascripts/preventDuplicateFormSubmissions.js',
      paths.src + 'javascripts/fullscreenTable.js',
      paths.src + 'javascripts/previewPane.js',
      paths.src + 'javascripts/colourPreview.js',
      paths.src + 'javascripts/templateFolderForm.js',
      paths.src + 'javascripts/collapsibleCheckboxes.js',
      paths.src + 'javascripts/main.js'
    ])
    .pipe(plugins.prettyerror())
    .pipe(plugins.babel({
      presets: ['@babel/preset-env']
    }))
    .pipe(plugins.addSrc.prepend([
      paths.npm + 'hogan.js/dist/hogan-3.0.2.js',
      paths.npm + 'jquery/dist/jquery.min.js',
      paths.npm + 'query-command-supported/dist/queryCommandSupported.min.js',
      paths.npm + 'diff-dom/diffDOM.js',
      paths.npm + 'timeago/jquery.timeago.js',
      paths.npm + 'textarea-caret/index.js',
      paths.src + 'javascripts/modules/all.js'
    ]))
    .pipe(plugins.uglify())
    .pipe(plugins.concat('all.js'))
    .pipe(dest(paths.dist + 'javascripts/'))
};


const sass = () => {
  return src([paths.src + '/stylesheets/main*.scss', paths.src + '/stylesheets/print.scss'])
    .pipe(plugins.prettyerror())
    .pipe(plugins.sass({
      outputStyle: 'compressed',
      includePaths: [
        paths.npm + 'govuk-elements-sass/public/sass/',
        paths.toolkit + 'stylesheets/',
        paths.govuk_frontend,
      ]
    }))
    .pipe(plugins.base64('../..'))
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
        'options': { 'formatter': 'stylish' }
      }))
      .pipe(plugins.sassLint.format())
      .pipe(plugins.sassLint.failOnError());
  },
  'js': (cb) => {
    return src(
        paths.src + 'javascripts/**/*.js',
        { ignore: paths.src + 'javascripts/modules/*.js' } // ignore bundler boilerplate JS
      )
      .pipe(plugins.jshint())
      .pipe(plugins.jshint.reporter(stylish))
      .pipe(plugins.jshint.reporter('fail'))
  }
};


// Default: compile everything
const defaultTask = parallel(
  series(
    copy.govuk_frontend.fonts,
    images
  ),
  series(
    copy.error_pages,
    series(
      bundleJavaScriptModules,
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
