// GULPFILE
// - - - - - - - - - - - - - - -
// This file processes all of the assets in the "src" folder
// and outputs the finished files in the "dist" folder.

// 1. LIBRARIES
// - - - - - - - - - - - - - - -
var gulp = require('gulp'),
    plugins = require('gulp-load-plugins')(),

// 2. CONFIGURATION
// - - - - - - - - - - - - - - -
    paths = {
        src: 'app/assets/',
        dist: 'app/static/',
        templates: 'app/templates/'
    };

// 3. TASKS
// - - - - - - - - - - - - - - -

// Move GOV.UK template resources

gulp.task('copy:govuk_template:template', () => gulp.src('bower_components/govuk_template/views/layouts/govuk_template.html')
  .pipe(gulp.dest(paths.templates))
);

gulp.task('copy:govuk_template:assets', () => gulp.src('bower_components/govuk_template/assets/**/*')
  .pipe(gulp.dest(paths.dist))
);

gulp.task('javascripts', () => gulp
  .src([
    paths.src + 'govuk_frontend_toolkit/javascripts/govuk/modules.js',
    paths.src + 'javascripts/highlightTags.js',
    paths.src + 'javascripts/dropdown.js',
    paths.src + 'javascripts/main.js'
  ])
  .pipe(plugins.babel({
    presets: ['es2015']
  }))
  .pipe(plugins.uglify())
  .pipe(plugins.addSrc.prepend(
    './node_modules/jquery/dist/jquery.min.js'
  ))
  .pipe(plugins.concat('all.js'))
  .pipe(gulp.dest(paths.dist + 'javascripts/'))
);

gulp.task('sass', () => gulp
  .src(paths.src + '/stylesheets/main*.scss')
  .pipe(plugins.sass({outputStyle: 'compressed'}))
  .pipe(gulp.dest(paths.dist + '/stylesheets'))
);


// Copy images

gulp.task('images', () => gulp
  .src(paths.src + 'images/**/*')
  .pipe(gulp.dest(paths.dist + '/images'))
);


// Watch for changes and re-run tasks
gulp.task('watchForChanges', function() {
  gulp.watch(paths.src + 'javascripts/**/*', ['javascripts']);
  gulp.watch(paths.src + 'stylesheets/**/*', ['sass']);
  gulp.watch(paths.src + 'images/**/*', ['images']);
});

// Default: compile everything
gulp.task('default',
    ['copy:govuk_template:template', 'copy:govuk_template:assets', 'javascripts', 'sass', 'images']
);

// Optional: recompile on changes
gulp.task('watch',
    ['default', 'watchForChanges']
);
