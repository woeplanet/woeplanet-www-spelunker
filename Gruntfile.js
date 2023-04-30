/* jshint -W069 */

sass = require('sass');
module.exports = function(grunt) {
    require('load-grunt-tasks')(grunt);

    grunt.initConfig({
        pkg: grunt.file.readJSON('package.json'),
        dirs: {
            static: 'static/'
        },
        clean: {
            dist: ['<%= dirs.static %>/']
        },
        concat: {
            main: {
                src: [
                    './node_modules/jquery/dist/jquery.js',
                    './node_modules/leaflet/dist/leaflet.js',
                    './node_modules/leaflet.sync/L.Map.Sync.js',
                    './src/js/location.js',
                    './src/js/results.js',
                    './src/js/map.js',
                    './src/js/label.js'
                ],
                dest: '<%= dirs.static %>/js/site.js'
            }
        },
        copy: {
            images: {
                files: [
                    {
                        expand: true,
                        cwd: 'src/icons',
                        src: ['**/*'],
                        dest: '<%= dirs.static %>/icons/'
                    },
                    {
                        expand: true,
                        cwd: 'node_modules/leaflet/dist/images',
                        src: ['**/*.png'],
                        dest: '<%= dirs.static %>/images/leaflet',
                        filter: 'isFile',
                        ext: '.png'
                    },
                    {
                        expand: true,
                        cwd: 'src/images',
                        src: ['**/*.jpg'],
                        dest: '<%= dirs.static %>/images/'
                    }
                ]
            },
            leaflet: {
                options: {
                    process: function (content, srcpath) {
                        // fixup Leaflet image paths ...
                        return content.replace(/images\//g, 'images/leaflet/');
                    }
                },
                files: [
                    {
                        expand: true,
                        cwd: './node_modules/leaflet/dist',
                        src: ['*.css'],
                        dest: 'src/scss/leaflet',
                        filter: 'isFile',
                        rename: function (dest, src) {
                            return dest + '/_' + src;
                        },
                        ext: '.scss'
                    },
                    {
                        expand: true,
                        cwd: './node_modules/leaflet/dist',
                        src: ['leaflet.js.map'],
                        dest: '<%= dirs.static %>/js/'
                    }
                ]
            },
            geojson: {
                files: [
                    {
                        expand: true,
                        cwd: './node_modules/null-island/GeoJSON',
                        src: 'null-island.geo.json',
                        dest: '<%= dirs.static %>/geojson/',
                        filter: 'isFile',
                        rename: function(dest, src) {
                            return dest + '/null-island.geojson'
                        }
                    }
                ]
            }
        },
        postcss: {
            options: {
                map: true,
                processors: [
                    require('autoprefixer')()
                ]
            },
            dist: {
                src: '<%= dirs.static %>/css/site.css'
            }
        },
        sass: {
            options: {
                implementation: sass,
                outputStyle: 'expanded',
                indentType: 'tab',
                indentWidth: 1,
                includePaths: [
                    './src/scss',
                    './src/scss/leaflet',
                    './node_modules/bootstrap/scss'
                ]
            },
            main: {
                files: {
                    '<%= dirs.static %>/css/site.css': 'src/scss/main.scss'
                }
            }
        },
        uglify: {
            dist: {
                options: {
                    sourceMap: true,
                    compress: {
                        drop_console: false // true
                    }
                },
                files: {
                    '<%= dirs.static %>/js/site.min.js': ['<%= dirs.static %>/js/site.js']
                }
            }
        },
        watch: {
            options: {
                livereload: true
            },
            grunt: {
                files: ['Gruntfile.js'],
                tasks: ['clean', 'build']
            },
            json: {
                files: ['package.json'],
                tasks: ['rebuild']
            },
            js: {
                files: ['./src/js/**/*.js'],
                tasks: ['concat:main', 'uglify']
            },
            scss: {
                files: ['./src/scss/**/*.scss'],
                tasks: ['sass', 'postcss']
            }
        }
    });

    grunt.registerTask('default', ['openport:watch.options.livereload:35729', 'watch']);
    grunt.registerTask('build', ['nodsstore', 'copy', 'concat', 'uglify', 'sass', 'postcss']);
    grunt.registerTask('rebuild', ['clean', 'build']);
    grunt.registerTask('nodsstore', function () {
        grunt.file.expand({
            'filter': 'isFile',
            'cwd': '.'
        }, ['**/.DS_Store']).forEach(function (file) {
            grunt.file.delete(file);
        });
    });
};