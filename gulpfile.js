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

gulp.task('copy:govuk_template:template', function() {
    return gulp.src('bower_components/govuk_template/views/layouts/govuk_template.html')
        .pipe(gulp.dest(paths.templates));
});

gulp.task('copy:govuk_template:assets', function() {
    return gulp.src('bower_components/govuk_template/assets/**/*')
        .pipe(gulp.dest(paths.dist));
});


// Concatenate and minify

gulp.task('javascripts', function() {
    return gulp.src(paths.src + 'javascripts/main.js')
        .pipe(plugins.include())
        .pipe(gulp.dest(paths.dist + 'javascripts/'))
        .pipe(plugins.uglify())
            .on('error', function(e) { console.log("Uglify did not complete."); })
        .pipe(gulp.dest(paths.dist + 'javascripts/'));

});

gulp.task('sass', function () {
    return gulp.src(paths.src + '/stylesheets/main*.scss')
        .pipe(plugins.sass({outputStyle: 'compressed'}))
        .pipe(gulp.dest(paths.dist + '/stylesheets'));
});


// Copy images

gulp.task('images', function() {
    return gulp.src(paths.src + 'images/**/*')
        .pipe(gulp.dest(paths.dist + '/images'));
});


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
